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

from colorama import init, Fore, Style
from tqdm import tqdm

from django.dispatch import receiver

from util import create_pbar, update_pbar, get_verbosity
from patchman.signals import pbar_start, pbar_update, info_message, warning_message, error_message, debug_message

from django.conf import settings

init(autoreset=True)


@receiver(pbar_start)
def pbar_start_receiver(**kwargs):
    """ Receiver to create a progressbar
    """
    ptext = kwargs.get('ptext')
    plen = kwargs.get('plen')
    if ptext and plen:
        create_pbar(ptext, plen)


@receiver(pbar_update)
def pbar_update_receiver(**kwargs):
    """ Receiver to update a progressbar
    """
    index = kwargs.get('index')
    if index:
        update_pbar(index)


@receiver(info_message)
def print_info_message(sender=None, **kwargs):
    """ Receiver to print an info message, no color
    """
    text = str(kwargs.get('text'))
    if get_verbosity():
        tqdm.write(Style.RESET_ALL + Fore.RESET + text)


@receiver(warning_message)
def print_warning_message(**kwargs):
    """ Receiver to print a warning message in yellow text
    """
    text = str(kwargs.get('text'))
    if get_verbosity():
        tqdm.write(Style.BRIGHT + Fore.YELLOW + text)


@receiver(error_message)
def print_error_message(**kwargs):
    """ Receiver to print an error message in red text
    """
    text = str(kwargs.get('text'))
    if text:
        tqdm.write(Style.BRIGHT + Fore.RED + text)


@receiver(debug_message)
def print_debug_message(**kwargs):
    """ Receiver to print a debug message in blue, if verbose and DEBUG are set
    """
    text = str(kwargs.get('text'))
    if get_verbosity() and settings.DEBUG and text:
        tqdm.write(Style.BRIGHT + Fore.BLUE + text)
