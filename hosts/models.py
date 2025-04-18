# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2021 Marcus Furlong <furlongm@gmail.com>
#
# This file is part of Patchman.
#
# Patchman is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 only.
#
# Patchman is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Patchman. If not, see <http://www.gnu.org/licenses/>

from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

try:
    from version_utils.rpm import labelCompare
except ImportError:
    from rpm import labelCompare
from taggit.managers import TaggableManager

from arch.models import MachineArchitecture
from domains.models import Domain
from errata.models import Erratum
from hosts.utils import update_rdns
from modules.models import Module
from operatingsystems.models import OSVariant
from packages.models import Package, PackageUpdate
from packages.utils import get_or_create_package_update
from patchman.signals import info_message
from repos.models import Repository
from repos.utils import find_best_repo


class Host(models.Model):

    hostname = models.CharField(max_length=255, unique=True)
    ipaddress = models.GenericIPAddressField()
    reversedns = models.CharField(max_length=255, blank=True, null=True)
    check_dns = models.BooleanField(default=False)
    osvariant = models.ForeignKey(OSVariant, on_delete=models.CASCADE)
    kernel = models.CharField(max_length=255)
    arch = models.ForeignKey(MachineArchitecture, on_delete=models.CASCADE)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    lastreport = models.DateTimeField()
    packages = models.ManyToManyField(Package, blank=True)
    repos = models.ManyToManyField(Repository, blank=True, through='HostRepo')
    modules = models.ManyToManyField(Module, blank=True)
    updates = models.ManyToManyField(PackageUpdate, blank=True)
    reboot_required = models.BooleanField(default=False)
    host_repos_only = models.BooleanField(default=True)
    tags = TaggableManager(blank=True)
    updated_at = models.DateTimeField(default=timezone.now)
    errata = models.ManyToManyField(Erratum, blank=True)

    from hosts.managers import HostManager
    objects = HostManager()

    class Meta:
        verbose_name = 'Host'
        verbose_name_plural = 'Hosts'
        ordering = ['hostname']

    def __str__(self):
        return self.hostname

    def show(self):
        """ Show info about this host
        """
        text = f'{self}:\n'
        text += f'IP address   : {self.ipaddress}\n'
        text += f'Reverse DNS  : {self.reversedns}\n'
        text += f'Domain       : {self.domain}\n'
        text += f'OS Variant   : {self.osvariant}\n'
        text += f'Kernel       : {self.kernel}\n'
        text += f'Architecture : {self.arch}\n'
        text += f'Last report  : {self.lastreport}\n'
        text += f'Packages     : {self.get_num_packages()}\n'
        text += f'Repos        : {self.get_num_repos()}\n'
        text += f'Updates      : {self.get_num_updates()}\n'
        text += f'Tags         : {self.tags}\n'
        text += f'Needs reboot : {self.reboot_required}\n'
        text += f'Updated at   : {self.updated_at}\n'
        text += f'Host repos   : {self.host_repos_only}\n'

        info_message.send(sender=None, text=text)

    def get_absolute_url(self):
        return reverse('hosts:host_detail', args=[self.hostname])

    def get_num_security_updates(self):
        return self.updates.filter(security=True).count()

    def get_num_bugfix_updates(self):
        return self.updates.filter(security=False).count()

    def get_num_updates(self):
        return self.updates.count()

    def get_num_packages(self):
        return self.packages.count()

    def get_num_repos(self):
        return self.repos.count()

    def check_rdns(self):
        if self.check_dns:
            update_rdns(self)
            if self.hostname.lower() == self.reversedns.lower():
                info_message.send(sender=None, text='Reverse DNS matches')
            else:
                text = 'Reverse DNS mismatch found: '
                text += f'{self.hostname} != {self.reversedns}'
                info_message.send(sender=None, text=text)
        else:
            info_message.send(sender=None, text='Reverse DNS check disabled')

    def clean_reports(self):
        """ Remove all but the last 3 reports for a host
        """
        from reports.models import Report
        reports = Report.objects.filter(host=self).order_by('-created')[3:]
        rlen = reports.count()
        for report in Report.objects.filter(host=self).order_by('-created')[3:]:
            report.delete()
        if rlen > 0:
            info_message.send(sender=None, text=f'{self.hostname}: removed {rlen} old reports')

    def get_host_repo_packages(self):
        if self.host_repos_only:
            hostrepos_q = Q(mirror__repo__in=self.repos.all(),
                            mirror__enabled=True,
                            mirror__repo__enabled=True,
                            mirror__repo__hostrepo__enabled=True)
        else:
            hostrepos_q = \
                Q(mirror__repo__osrelease__osvariant__host=self,
                  mirror__repo__arch=self.arch,
                  mirror__enabled=True,
                  mirror__repo__enabled=True) | \
                Q(mirror__repo__in=self.repos.all(),
                  mirror__enabled=True,
                  mirror__repo__enabled=True)
        return Package.objects.select_related().filter(hostrepos_q).distinct()

    def process_update(self, package, highest_package):
        if self.host_repos_only:
            host_repos = Q(repo__host=self)
        else:
            host_repos = Q(repo__osrelease__osvariant__host=self, repo__arch=self.arch) | Q(repo__host=self)
        mirrors = highest_package.mirror_set.filter(host_repos)
        security = False
        # if any of the containing repos are security, mark the update as a security update
        for mirror in mirrors:
            if mirror.repo.security:
                security = True
        update = get_or_create_package_update(oldpackage=package, newpackage=highest_package, security=security)
        self.updates.add(update)
        info_message.send(sender=None, text=f'{update}')
        return update.id

    def find_updates(self):

        kernels_q = Q(name__name='kernel') | \
            Q(name__name='kernel-devel') | \
            Q(name__name='kernel-preempt') | \
            Q(name__name='kernel-preempt-devel') | \
            Q(name__name='kernel-rt') | \
            Q(name__name='kernel-rt-devel') | \
            Q(name__name='kernel-debug') | \
            Q(name__name='kernel-debug-devel') | \
            Q(name__name='kernel-default') | \
            Q(name__name='kernel-default-devel') | \
            Q(name__name='kernel-headers') | \
            Q(name__name='kernel-core') | \
            Q(name__name='kernel-modules') | \
            Q(name__name='virtualbox-kmp-default') | \
            Q(name__name='virtualbox-kmp-preempt') | \
            Q(name__name='kernel-uek') | \
            Q(name__name='kernel-uek-devel') | \
            Q(name__name='kernel-uek-debug') | \
            Q(name__name='kernel-uek-debug-devel') | \
            Q(name__name='kernel-uek-container') | \
            Q(name__name='kernel-uek-container-debug') | \
            Q(name__name='kernel-uek-doc')
        repo_packages = self.get_host_repo_packages()
        host_packages = self.packages.exclude(kernels_q).distinct()
        kernel_packages = self.packages.filter(kernels_q)

        if self.host_repos_only:
            update_ids = self.find_host_repo_updates(host_packages, repo_packages)
        else:
            update_ids = self.find_osrelease_repo_updates(host_packages, repo_packages)

        kernel_update_ids = self.find_kernel_updates(kernel_packages, repo_packages)
        for ku_id in kernel_update_ids:
            update_ids.append(ku_id)

        for update in self.updates.all():
            if update.id not in update_ids:
                self.updates.remove(update)

    def find_host_repo_updates(self, host_packages, repo_packages):

        update_ids = []
        hostrepos_q = Q(repo__mirror__enabled=True,
                        repo__mirror__refresh=True,
                        repo__mirror__repo__enabled=True,
                        host=self)
        hostrepos = HostRepo.objects.select_related().filter(hostrepos_q)

        for package in host_packages:
            highest_package = package
            best_repo = find_best_repo(package, hostrepos)
            priority = None
            if best_repo is not None:
                priority = best_repo.priority

            # find the packages that are potential updates
            pu_q = Q(
                name=package.name,
                arch=package.arch,
                packagetype=package.packagetype,
                category=package.category,
            )
            potential_updates = repo_packages.filter(pu_q).exclude(version__startswith='9999')
            for pu in potential_updates:
                pu_is_module_package = False
                pu_in_enabled_modules = False
                if pu.module_set.exists():
                    pu_is_module_package = True
                    for module in pu.module_set.all():
                        if module in self.modules.all():
                            pu_in_enabled_modules = True
                if pu_is_module_package:
                    if not pu_in_enabled_modules:
                        continue
                if package.compare_version(pu) == -1:
                    # package updates that are fixed by erratum (may already be superceded by another update)
                    errata = pu.provides_fix_in_erratum.all()
                    if errata:
                        for erratum in errata:
                            self.errata.add(erratum)
                    if highest_package.compare_version(pu) == -1:
                        if priority is not None:
                            # proceed only if the package is from a repo with a
                            # priority and that priority is >= the repo priority
                            pu_best_repo = find_best_repo(pu, hostrepos)
                            if pu_best_repo:
                                pu_priority = pu_best_repo.priority
                                if pu_priority >= priority:
                                    highest_package = pu
                        else:
                            highest_package = pu

            if highest_package != package:
                uid = self.process_update(package, highest_package)
                if uid is not None:
                    update_ids.append(uid)
        return update_ids

    def find_osrelease_repo_updates(self, host_packages, repo_packages):

        update_ids = []
        for package in host_packages:
            highest_package = package

            # find the packages that are potential updates
            pu_q = Q(name=package.name,
                     arch=package.arch,
                     packagetype=package.packagetype)
            potential_updates = repo_packages.filter(pu_q)
            for pu in potential_updates:
                pu_is_module_package = False
                pu_in_enabled_modules = False
                if pu.module_set.exists():
                    pu_is_module_package = True
                    for module in pu.module_set.all():
                        if module in self.modules.all():
                            pu_in_enabled_modules = True
                if pu_is_module_package:
                    if not pu_in_enabled_modules:
                        continue
                if package.compare_version(pu) == -1:
                    # package updates that are fixed by erratum (may already be superceded by another update)
                    errata = pu.provides_fix_in_erratum.all()
                    if errata:
                        for erratum in errata:
                            self.errata.add(erratum)
                    if highest_package.compare_version(pu) == -1:
                        highest_package = pu

            if highest_package != package:
                uid = self.process_update(package, highest_package)
                if uid is not None:
                    update_ids.append(uid)
        return update_ids

    def check_if_reboot_required(self, host_highest):

        ver, rel = self.kernel.split('-')[:2]
        kernel_ver = ('', str(ver), str(rel))
        host_highest_ver = ('', host_highest.version, host_highest.release)
        if labelCompare(kernel_ver, host_highest_ver) == -1:
            self.reboot_required = True
        else:
            self.reboot_required = False
        self.save()

    def find_kernel_updates(self, kernel_packages, repo_packages):

        update_ids = []
        for package in kernel_packages:
            host_highest = package
            repo_highest = package

            pu_q = Q(name=package.name)
            potential_updates = repo_packages.filter(pu_q)
            for pu in potential_updates:
                if package.compare_version(pu) == -1 \
                        and repo_highest.compare_version(pu) == -1:
                    repo_highest = pu

            host_packages = self.packages.filter(pu_q)
            for hp in host_packages:
                if package.compare_version(hp) == -1 and \
                        host_highest.compare_version(hp) == -1:
                    host_highest = hp

            if host_highest.compare_version(repo_highest) == -1:
                uid = self.process_update(host_highest, repo_highest)
                if uid is not None:
                    update_ids.append(uid)

            self.check_if_reboot_required(host_highest)
        return update_ids


class HostRepo(models.Model):
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    repo = models.ForeignKey(Repository, on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)

    class Meta:
        unique_together = ['host', 'repo']

    def __str__(self):
        return f'{self.host}-{self.repo}'
