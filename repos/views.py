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

from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse
from django.db.models import Q
from django.contrib import messages
from django.db import IntegrityError

from rest_framework import viewsets

from util.filterspecs import Filter, FilterBar
from hosts.models import HostRepo
from repos.models import Repository, Mirror, MirrorPackage
from operatingsystems.models import OSRelease
from arch.models import MachineArchitecture
from repos.forms import EditRepoForm, LinkRepoForm, CreateRepoForm, EditMirrorForm
from repos.serializers import RepositorySerializer, MirrorSerializer, MirrorPackageSerializer


@login_required
def repo_list(request):

    repos = Repository.objects.select_related().order_by('name')

    if 'repotype' in request.GET:
        repos = repos.filter(repotype=request.GET['repotype'])

    if 'arch_id' in request.GET:
        repos = repos.filter(arch=request.GET['arch_id'])

    if 'osrelease_id' in request.GET:
        repos = repos.filter(osrelease=request.GET['osrelease_id'])

    if 'security' in request.GET:
        security = request.GET['security'] == 'true'
        repos = repos.filter(security=security)

    if 'enabled' in request.GET:
        enabled = request.GET['enabled'] == 'true'
        repos = repos.filter(enabled=enabled)

    if 'package_id' in request.GET:
        repos = repos.filter(mirror__packages=request.GET['package_id'])

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains=term)
            query = query & q
        repos = repos.filter(query)
    else:
        terms = ''

    repos = repos.distinct()

    page_no = request.GET.get('page')
    paginator = Paginator(repos, 50)

    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    filter_list = []
    filter_list.append(Filter(request, 'OS Release', 'osrelease_id', OSRelease.objects.filter(repos__in=repos)))
    filter_list.append(Filter(request, 'Enabled', 'enabled', {'true': 'Yes', 'false': 'No'}))
    filter_list.append(Filter(request, 'Security', 'security', {'true': 'Yes', 'false': 'No'}))
    filter_list.append(Filter(request, 'Repo Type', 'repotype', Repository.REPO_TYPES))
    filter_list.append(Filter(request, 'Architecture', 'arch_id',
                              MachineArchitecture.objects.filter(repository__in=repos)))
    filter_bar = FilterBar(request, filter_list)

    return render(request,
                  'repos/repo_list.html',
                  {'page': page,
                   'filter_bar': filter_bar,
                   'terms': terms})


@login_required
def mirror_list(request):

    def pre_reqs(arch, repotype):
        for mirror in mirrors:
            if mirror.repo.arch != arch:
                text = 'Not all mirror architectures are the same,'
                text += ' cannot link to or create repos'
                messages.info(request, text)
                return render(request, 'repos/mirror_with_repo_list.html', {'page': page, 'checksum': checksum})

            if mirror.repo.repotype != repotype:
                text = 'Not all mirror repotypes are the same,'
                text += ' cannot link to or create repos'
                messages.info(request, text)
                return render(request,
                              'repos/mirror_with_repo_list.html',
                              {'page': page, 'checksum': checksum})
        return True

    def move_mirrors(repo):
        for mirror in mirrors:
            oldrepo = mirror.repo
            for hostrepo in HostRepo.objects.filter(repo=oldrepo):
                try:
                    hostrepo.repo = repo
                    hostrepo.save()
                except IntegrityError:
                    hostrepo.delete()
            mirror.repo = repo
            mirror.save()
            if oldrepo.mirror_set.count() == 0:
                oldrepo.delete()

    mirrors = Mirror.objects.select_related().order_by('packages_checksum')

    checksum = None
    if 'checksum' in request.GET:
        checksum = request.GET['checksum']
    if 'checksum' in request.POST:
        checksum = request.POST['checksum']
    if checksum is not None:
        mirrors = mirrors.filter(packages_checksum=checksum)

    if 'repo_id' in request.GET:
        mirrors = mirrors.filter(repo=request.GET['repo_id'])

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(url__icontains=term)
            query = query & q
        mirrors = mirrors.filter(query)
    else:
        terms = ''

    mirrors = mirrors.distinct()

    page_no = request.GET.get('page')
    paginator = Paginator(mirrors, 50)

    try:
        page = paginator.page(page_no)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    if request.method == 'POST':
        arch = mirrors[0].repo.arch
        repotype = mirrors[0].repo.repotype

        enabled = mirrors[0].repo.enabled
        security = mirrors[0].repo.security

        create_form = CreateRepoForm(request.POST, prefix='create', arch=arch,
                                     repotype=repotype)
        if create_form.is_valid():
            repo = create_form.save(commit=False)
            repo.arch = create_form.arch
            repo.repotype = create_form.repotype
            repo.enabled = enabled
            repo.security = security
            repo.save()
            move_mirrors(repo)
            text = f'Mirrors linked to new Repository {repo}'
            messages.info(request, text)
            return redirect(repo.get_absolute_url())

        link_form = LinkRepoForm(request.POST, prefix='link')
        if link_form.is_valid():
            repo = link_form.cleaned_data['name']
            move_mirrors(repo)
            text = f'Mirrors linked to Repository {repo}'
            messages.info(request, text)
            return redirect(repo.get_absolute_url())
    else:
        if 'checksum' in request.GET and mirrors:
            arch = mirrors[0].repo.arch
            repotype = mirrors[0].repo.repotype
            prereqs = pre_reqs(arch, repotype)
            if not prereqs:
                return prereqs
            else:
                link_form = LinkRepoForm(prefix='link')
                create_form = CreateRepoForm(prefix='create')
                return render(request,
                              'repos/mirror_with_repo_list.html',
                              {'page': page,
                               'link_form': link_form,
                               'create_form': create_form,
                               'checksum': checksum})
    return render(request,
                  'repos/mirror_list.html',
                  {'page': page})


@login_required
def mirror_detail(request, mirror_id):
    mirror = get_object_or_404(Mirror, id=mirror_id)
    return render(request,
                  'repos/mirror_detail.html',
                  {'mirror': mirror})


@login_required
def mirror_delete(request, mirror_id):
    mirror = get_object_or_404(Mirror, id=mirror_id)

    if request.method == 'POST':
        if 'delete' in request.POST:
            mirror.delete()
            text = f'Mirror {mirror} has been deleted'
            messages.info(request, text)
            return redirect(reverse('repos:mirror_list'))
        elif 'cancel' in request.POST:
            return redirect(mirror.get_absolute_url())

    return render(request,
                  'repos/mirror_delete.html',
                  {'mirror': mirror})


@login_required
def mirror_edit(request, mirror_id):

    mirror = get_object_or_404(Mirror, id=mirror_id)

    if request.method == 'POST':
        if 'save' in request.POST:
            edit_form = EditMirrorForm(request.POST, instance=mirror)
            if edit_form.is_valid():
                mirror = edit_form.save()
                mirror.save()
                text = f'Saved changes to Mirror {mirror}'
                messages.info(request, text)
                return redirect(mirror.get_absolute_url())
            else:
                mirror = get_object_or_404(Mirror, id=mirror_id)
        elif 'cancel' in request.POST:
            return redirect(mirror.get_absolute_url())
    else:
        edit_form = EditMirrorForm(instance=mirror)

    return render(request,
                  'repos/mirror_edit.html',
                  {'mirror': mirror, 'edit_form': edit_form})


@login_required
def repo_detail(request, repo_id):

    repo = get_object_or_404(Repository, id=repo_id)

    return render(request,
                  'repos/repo_detail.html',
                  {'repo': repo})


@login_required
def repo_edit(request, repo_id):

    repo = get_object_or_404(Repository, id=repo_id)

    if request.method == 'POST':
        if 'save' in request.POST:
            edit_form = EditRepoForm(request.POST, instance=repo)
            if edit_form.is_valid():
                repo = edit_form.save()
                repo.save()
                mirrors = edit_form.cleaned_data['mirrors']
                for mirror in mirrors:
                    mirror.repo = repo
                    mirror.save()
                if repo.enabled:
                    repo.enable()
                else:
                    repo.disable()
                text = f'Saved changes to Repository {repo}'
                messages.info(request, text)
                return redirect(repo.get_absolute_url())
            else:
                repo = get_object_or_404(Repository, id=repo_id)
        elif 'cancel' in request.POST:
            return redirect(repo.get_absolute_url())
    else:
        edit_form = EditRepoForm(instance=repo)
        edit_form.initial['mirrors'] = repo.mirror_set.all()

    return render(request,
                  'repos/repo_edit.html',
                  {'repo': repo, 'edit_form': edit_form})


@login_required
def repo_delete(request, repo_id):

    repo = get_object_or_404(Repository, id=repo_id)

    if request.method == 'POST':
        if 'delete' in request.POST:
            for mirror in repo.mirror_set.all():
                mirror.delete()
            repo.delete()
            text = f'Repository {repo} has been deleted'
            messages.info(request, text)
            return redirect(reverse('repos:repo_list'))
        elif 'cancel' in request.POST:
            return redirect(repo.get_absolute_url())

    return render(request,
                  'repos/repo_delete.html',
                  {'repo': repo})


@login_required
def repo_toggle_enabled(request, repo_id):

    repo = get_object_or_404(Repository, id=repo_id)
    if repo.enabled:
        repo.enabled = False
        status = 'disabled'
    else:
        repo.enabled = True
        status = 'enabled'
    repo.save()
    if request.is_ajax():
        return HttpResponse(status=204)
    else:
        text = f'Repository {repo} has been {status}'
        messages.info(request, text)
        return redirect(repo.get_absolute_url())


@login_required
def repo_toggle_security(request, repo_id):

    repo = get_object_or_404(Repository, id=repo_id)
    if repo.security:
        repo.security = False
        sectype = 'non-security'
    else:
        repo.security = True
        sectype = 'security'
    repo.save()
    if request.is_ajax():
        return HttpResponse(status=204)
    else:
        text = f'Repository {repo} has been marked'
        text += f' as a {sectype} update repo'
        messages.info(request, text)
        return redirect(repo.get_absolute_url())


@login_required
def repo_refresh(request, repo_id):
    """ Refresh a repo using a celery task
    """
    from repos.tasks import refresh_repo
    repo = get_object_or_404(Repository, id=repo_id)
    refresh_repo.delay(repo.id)
    text = f'Repostory {repo} is being refreshed'
    messages.info(request, text)
    return redirect(repo.get_absolute_url())


class RepositoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows repositories to be viewed or edited.
    """
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer


class MirrorViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows mirrors to be viewed or edited.
    """
    queryset = Mirror.objects.all()
    serializer_class = MirrorSerializer


class MirrorPackageViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows mirror packages to be viewed or edited.
    """
    queryset = MirrorPackage.objects.all()
    serializer_class = MirrorPackageSerializer
