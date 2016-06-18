# Copyright 2012 VPAC, http://www.vpac.org
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

import os
import sys
import string
from colorama import Fore, Style

from progressbar import Bar, ETA, Percentage, ProgressBar

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patchman.settings")
from django.conf import settings

pbar = None
verbose = None


def get_verbosity():
    """ Get the global verbosity level
    """
    global verbose
    return verbose


def set_verbosity(value):
    """ Set the global verbosity level
    """
    global verbose
    verbose = value


def create_pbar(ptext, plength, **kwargs):
    """ Create a global progress bar if global verbose is True
    """
    global pbar, verbose
    if verbose and plength > 0:
        jtext = string.ljust(ptext, 35)
        pbar = ProgressBar(widgets=[Style.RESET_ALL + Fore.YELLOW + jtext,
                                    Percentage(), Bar(), ETA()],
                           maxval=plength).start()
        return pbar


def update_pbar(index, **kwargs):
    """ Update the global progress bar if global verbose is True
    """
    global pbar, verbose
    if verbose and pbar:
        pbar.update(index)
        if index == pbar.maxval:
            pbar.finish()
            print_nocr(Fore.RESET)
            pbar = None


def download_url(res, text=''):
    """ Display a progress bar to download the request content if verbose is
        True. Otherwise, just return the request content
    """
    global verbose
    if verbose and 'content-length' in res.headers:
        clen = int(res.headers['content-length'])
        create_pbar(text, clen)
        chunk_size = 16384
        i = 0
        data = b''
        for chunk in res.iter_content(chunk_size):
            i += len(chunk)
            if i <= clen:
                update_pbar(i)
            data += chunk
        return data
    else:
        return res.content


def print_nocr(text):
    """ Print text without a carriage return
    """
    print text,
    sys.stdout.softspace = False
