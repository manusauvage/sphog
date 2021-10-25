#! /usr/bin/env python
#coding: utf-8
""" A simple script to generate static photo galleries

Copyright © 2020 Emmanuel le Chevoir

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.

"""

from __future__ import print_function

import os, sys, re, os.path, codecs
import zipfile
import configparser
import argparse

from PIL import Image
from jinja2 import  Environment, FileSystemLoader

from .album import Album
from .albumset import AlbumSet
from .utils import info, get_current_path
from .settings import settings

# Python2 does not know about FileNotFoundError, map it if needed
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


def get_input(prompt):
    # python3 has no raw_input, and input has a potentially risky behaviour in python2. Try to fix that.
    if not 'raw_input' in dir(__builtins__):
        raw_input = input
    return raw_input(prompt)

def build_index_def():
    base_template = '[directory]\ntitle: {title}\ndesc: {desc}\n'
    validation = False
    default_title = os.path.basename(get_current_path())
    answers = dict()
    while not validation:
        answers['title'] = get_input('    >>> Directory title [{}]: '.format(default_title))
        if answers['title'] == '': answers['title'] = default_title
        answers['desc'] = get_input('    >>> Description: ')
        ans = get_input ("\nI: The following index.def file will be written:\n    {:-^80s}\n    {}{:-^80s}\n\n    >>> Is that correct? [Y|n]".format('', '\n    '.join(base_template.format(**answers).split('\n')), ''))
        if ans == '' or ans.upper() == 'Y': validation = True
    print ('\n')
    with codecs.open('index.def', 'wb', 'utf8') as out:
        out.write(base_template.format(**answers))

def build_album_def():
    base_template = '[album]\ntitle: {title}\ndesc: {desc}\ndate: {date}\n'
    validation = False
    default_title = os.path.basename(get_current_path())
    answers = dict()
    while not validation:
        answers['title'] = get_input('    >>> Album title [{}]: '.format(default_title))
        if answers['title'] == '': answers['title'] = default_title
        answers['desc'] = get_input('    >>> Description: ')
        answers['date'] = get_input('    >>> Date: ')
        ans = get_input ("\nI: The following album.def file will be written:\n    {:-^80s}\n    {}{:-^80s}\n\n    >>> Is that correct? [Y|n]".format('', '\n    '.join(base_template.format(**answers).split('\n')), ''))
        if ans == '' or ans.upper() == 'Y': validation = True
    print ('\n')
    with codecs.open('album.def', 'wb', 'utf8') as out:
        out.write(base_template.format(**answers))

def build_album(site_config, regen=False, interactive=False):
    try: 
        album = Album(site_config, regen)
        info ('Building album [{}]'.format(album.base))
        album.prepare()
        album.render()
    except FileNotFoundError as e:
        if interactive is True:
            info ('No album.def found, switching to interactive mode')
            build_album_def()
            build_album(site_config, regen)
        else:
            error (e)
    except:
        raise

def build_index(site_config, recurse=False, build_albums=False, regen=False, interactive=False):
    try:
        albumset = AlbumSet(site_config, recurse, build_albums, regen)
        info ('Building directory index [{}]'.format(albumset.url))
        # FIXME: add option to specify output file name
        # albumset.render(output_file='index.test.html')
        albumset.render()
    except FileNotFoundError as e:
        if interactive is True:
            info ('No index.def found, switching to interactive mode')
            build_index_def()
            build_index(site_config, recurse, build_albums, regen)
        else:
            error (e)
    except: # FIXME: what kind of other exceptions do we expect?
        raise



#if __name__ == '__main__':

def main():
    # Parse command line. FIXME: this needs to be properly documented
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', help='Print more details about the ongoing task')
    parser.add_argument('-q', '--quiet', action='store_true', help="Don't display anything (except warnings and errors)")
    parser.add_argument('-r', '--recurse', action='store_true', help='Generate index files and albums for the entire subtree')
    parser.add_argument('-b', '--build-albums', action='store_true', help='Generate album files in the directory set')
    parser.add_argument('-f', '--force-regen', action='store_true', help='Force the regeneration of all album data')
    args = parser.parse_args()
    settings.verbose = args.verbose
    settings.quiet = args.quiet

    # Read the site config in the script main directory, and the album config in the current directory
    # The site config provides default values. All parameters can be overriden by the album config.
    # FIXME: this should probably be reworked to avoid writing a config in the script dir, but this will
    # FIXME: have to do for now.
    site_config = os.path.join(os.path.dirname(sys.argv[0]), 'site.config')


    # try generating an index first
    if os.path.exists('index.def'):
        build_index(site_config, recurse=args.recurse, build_albums=args.build_albums, regen=args.force_regen)
        sys.exit(0)

    # otherwise, deal with the album or index if there is one
    if os.path.exists('photos'):
        build_album(site_config, regen=args.force_regen, interactive=True)
    else:
        build_index(site_config, interactive=True)
