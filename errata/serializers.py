# Copyright 2025 Marcus Furlong <furlongm@gmail.com>
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

from rest_framework import serializers

from errata.models import Erratum, ErratumReference


class ErratumSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Erratum
        fields = ('id', 'name', 'e_type', 'issue_date', 'synopsis', 'cves', 'releases', 'references')


class ErratumReferenceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ErratumReference
        fields = ('id', 'er_type', 'url')
