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
from tqdm import tqdm

# Python2 does not know about FileNotFoundError, map it if needed
try:
	FileNotFoundError
except NameError:
	FileNotFoundError = IOError

# Python2 os.getcwd returns ascii paths, we need unicode
def get_current_path():
	try:
		# python2: call getcwdu()
		path = os.getcwdu()
	except AttributeError:
		# python3 returns unicode by default
		path = os.getcwd()
	return path

# Helper functions to report the script status.
# note: python logging seems a little overkill for our needs, so we don't use it
global g_verbose
global g_info
global g_quiet 
g_verbose = False
g_info = True
g_quiet = False
def verbose(message):
	if g_verbose == True and g_quiet == False:
		print (u'    | {}'.format(message))
def info(message):
	if g_info == True and g_quiet == False:
		print (u'I: {}'.format(message))
def warn(message):
	print (u'W: {}'.format(message), file=sys.stderr)
def error(message):
	print (u'E: {}'.format(message), file=sys.stderr)


# Helper function to crop a square image from a rectangle image
def crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))

# Helper function to generate a square thumbnail from a large picture
def gen_thumbnail(file_in, file_out, width=450):
	im = Image.open(file_in)
	im_thumb = crop_center(im, min(im.size), min(im.size)).resize((width, width), Image.LANCZOS)
	im_thumb.save(file_out, quality=95)


class AlbumSet(object):
	def __init__(self, site_config, recurse=False, build_albums=False, regen=False):
		dir_config = 'index.def'
		if not os.path.isfile(dir_config):
			raise FileNotFoundError('E: Could not read {} file'.format(dir_config))
		config = configparser.ConfigParser()
		config.read([site_config, dir_config], encoding='utf8')
		self.config        = config
		self._recurse      = recurse
		self._build_albums = build_albums
		self.regen         = regen
		self.name          = config.get('directory', 'title')
		self.desc          = config.get('directory', 'desc')
		self.stylesheet    = config.get('directory', 'stylesheet')
		self.thumbnail     = config.get('directory', 'thumbnail')
		self.template      = config.get('directory', 'template')
		self.exclude       = self._parse_list(config.get('directory', 'exclude', fallback=''))
		self.order         = self._parse_list(config.get('directory', 'order', fallback=''))
		self.type          = 'albumset'
		self.path          = get_current_path()
		self.url = u'{}'.format(re.sub(r'^{}'.format(self.config.get('global', 'siteroot')), '/', self.path)).replace('//', '/')
		if self.url[-1] == '/': self.url = self.url[:-1]
		self.parent        = self._get_parent()
		self.children      = self._get_children(site_config)

	def _parse_list(self, list_str):
		if list_str is '': return []
		try:
			return list(map(unicode.strip, list_str.split(',')))
		except NameError:
			# python3 deals with unicode by default
			return list(map(str.strip, list_str.split(',')))

	def _get_parent(self):
		parent = os.path.abspath(os.path.join(self.path, os.pardir))
		siteroot = self.config.get('global', 'siteroot')
		return u'{}'.format(re.sub(r'^{}'.format(siteroot), '/', parent)).replace('//', '/')

	def _sort_children(self):
		# copy the original list so elements can be removed without affecting the original list
		try:
			baselist = self.children.copy()
		except AttributeError: # Python2 has no list.copy()
			import copy
			baselist = copy.copy(self.children)
		destlist = []
		for refpath in self.order:
			# iterate on self.children and not its copy
			# to prevent messing with the actual iterable inside the for loop
			for item in self.children:
				basename = os.path.basename(item.path)
				if basename == refpath:
					# add matching item to the destlist and 
					# remove it from the baselist
					destlist.append(item)
					baselist.remove(item)
		# All config directories have been considered. If some elements remain,
		# add them to the end of destlist.
		if len(baselist) > 0:
			for item in baselist:
				destlist.append(item)
		return destlist

	def _get_children(self, site_config):
		self.children = []
		curpath = get_current_path()
		for (dirpath, dirs, files) in os.walk(self.path):
			# only walk the current directory, skip the subdirs
			if dirpath != curpath:
				continue
			for d in dirs:
				if d in self.exclude:
					continue
				if os.path.exists(os.path.join(d, 'album.def')):
					# craft Album object here
					os.chdir(d)
					try:
						album = Album(site_config, self.regen)
						album._parse_photodir()
						if self._build_albums:
							info (u'Building album [{}]'.format(album.base))
							album.prepare()
							album.render()
						self.children.append(album)
					except Exception as e:
						warn(u'something went wrong when building album in {}:\n{}'.format(d, e))
					os.chdir(self.path)
				elif os.path.exists(os.path.join(d, 'index.def')):
					# craft AlbumSet object here
					os.chdir(d)
					try:
						# don't build nested albums if recurse is disabled
						build_albums = self._recurse and self._build_albums
						album_set = AlbumSet(site_config, self._recurse, build_albums, self.regen)
						if self._recurse:
							info (u'Building directory index [{}]'.format(album_set.url))
							album_set.render()
						self.children.append(album_set)
					except Exception as e: 
						warn (u'something went wrong when building album set in {}\n{}'.format(d, e))
					os.chdir(self.path)
					pass
				else:
					# do nothing
					pass
		return self._sort_children()

	'''Render current album set using the appropriate template.'''
	def render(self, output_file='index.html'):
		env = Environment(loader=FileSystemLoader(searchpath=self.config.get('global', 'templatedir')))
		template = env.get_template(self.template)
		out = codecs.open(output_file, 'wb', 'utf8')
		tmp_output = template.render(directory=self)
		out.write(tmp_output)
		out.close()
		os.chmod(output_file, 0o644)



class Album(object):
	def __init__(self, site_config, regen=False):
		# FIXME: Album config file is hardcoded, but this is a tough one:
		# FIXME: at some point we need a file to hold our properties.
		# FIXME: This might be solved by specifying the path in site_config,
		# FIXME: but this would not be a major improvement (and it would need to config reads.)
		album_config = 'album.def'
		if not os.path.isfile(album_config):
			raise FileNotFoundError('E: Could not read {} file'.format(album_config))
		config = configparser.ConfigParser()
		config.read([site_config, album_config], encoding='utf8')
		self.config     = config
		self.name       = config.get('album', 'title')
		self.desc       = config.get('album', 'desc')
		if config.has_option('album', 'index_desc'):
			self.index_desc = config.get('album', 'index_desc')
		else:
			self.index_desc = self.desc
		self.date       = config.get('album', 'date')
		self.archive    = config.get('album', 'zipfile', fallback='')
		self.template   = config.get('album', 'template')
		self.stylesheet = config.get('album', 'stylesheet')
		self.thumbnail  = config.get('album', 'thumbnail')
		self.thumbnail_src = config.get('album', 'thumbnail_src', fallback='')
		self.thumbnail_size = config.getint('album', 'thumbnail_size')
		self.photodir   = config.get('album', 'photodir')
		self.count      = 0
		self.type       = 'album'
		self.path       = get_current_path()
		self.base       = u'/{}/'.format(self.path.replace(config.get('global', 'siteroot'), '')).replace('//', '/')
		self.url        = self.base
		self.regen      = regen
		if self.url[-1] == '/': self.url = self.url[:-1]
		try:
			self.parent  = config.get('album', 'parent')
		except configparser.NoOptionError:
			self.parent = self._get_parent()
		self._photos = []

	def __iter__(self):
		for p in sorted(self._photos, key=lambda p: p.filename):
			yield p

	def add(self, photo):
		photo.config = self.config
		self._photos.append(photo)
		self.count += 1

	def _get_parent(self):
		parent = os.path.abspath(os.path.join(self.path, os.pardir))
		siteroot = self.config.get('global', 'siteroot')
		return u'{}'.format(re.sub(r'^{}'.format(siteroot), '/', parent)).replace('//', '/')

	def _parse_photodir(self):
		# parse album.photodir to find original photos and add them to the object's list
		for dirname, dirnames, filenames in os.walk(self.photodir):
			for f in filenames:
				if not re.match('\.jpg', f[-4:], re.I):
					continue
				thumb   = self.config.get('photos', 'thumb_prefix')
				preview = self.config.get('photos', 'preview_prefix')
				if re.match('^(%s|%s)'%(thumb, preview), f):
					continue
				# Only consider photos located directly in photodir, ignore subdirs
				if os.path.exists(os.path.join(self.photodir, f)):
					self.add(Photo(os.path.join(self.photodir, f), self.config))

	def _zip_files(self):
		if os.path.exists(self.archive):
			if self.regen == False:
				verbose ('zip archive {} already created'.format(self.archive))
				return
			else:
				verbose ('Removing existing zip archive [{}]'.format(self.archive))
				os.remove(self.archive)
		verbose ('Creating zip archive...')
		z = zipfile.ZipFile(self.archive, 'w')
		for p in self._photos:
			z.write(p.path)
		z.close()
		os.chmod(self.archive, 0o644)

	def prepare(self):
		self._photos = []
		self.count = 0
		self._parse_photodir()
		# now we have the list of original photos, generate thumbnails and preview, if needed
		self._photos = sorted(self._photos, key=lambda p: p.filename)
		# If no photo has been designated as a source for the album picture, take the first one that comes
		if self.thumbnail_src == '' and len(self._photos) > 0:
			self.thumbnail_src = self._photos[0].path
		if not os.path.isfile(self.thumbnail) or self.regen == True:
			verbose (u'Generating album thumbnail ({})'.format(self.thumbnail))
			gen_thumbnail(self.thumbnail_src, self.thumbnail, self.thumbnail_size)
			os.chmod(self.thumbnail, 0o644)
		prev = None
		verbose ("Generating thumbnails and preview images...")
		barfmt = '    |{bar}|{percentage:3.0f}% ({n_fmt}/{total_fmt}) [{elapsed}<{remaining}]'
		progress = tqdm(self._photos, ncols=80, position=0, bar_format=barfmt, leave=False, disable=g_quiet)
		for p in progress:
			os.chmod(p.path, 0o644)
			p._extract_desc(default=self.desc)
			if not os.path.exists(p.thumb_path) or self.regen == True:
				thumb = Image.open(p.path)
				thumb = thumb.resize(p.get_thumb_size(), Image.ANTIALIAS)
				thumb.save(p.thumb_path)
				os.chmod(p.thumb_path, 0o644)
			if not os.path.exists(p.preview_path) or self.regen == True:
				preview = Image.open(p.path)
				preview = preview.resize(p.get_preview_size(), Image.ANTIALIAS)
				preview.save(p.preview_path)
				os.chmod(p.preview_path, 0o644)
			if prev:
				prev.next = p
			p.prev = prev
			prev = p
		# Create an archive containing the original photos, if requested
		if self.archive != '':
			self._zip_files()

	'''Render current album using the appropriate template. 
           FIXME: Output file is hardcoded to index.html, maybe this should change'''
	def render(self, output_file='index.html'):
		env = Environment(loader=FileSystemLoader(searchpath=self.config.get('global', 'templatedir')))
		template = env.get_template(self.template)
		out = codecs.open(output_file, 'wb', 'utf8')
		tmp_output = template.render(album=self)
		out.write(tmp_output)
		out.close()
		os.chmod(output_file, 0o644)



class Photo(object):
	def __init__(self, path, config, pprev=None, pnext=None, title=None):
		self.path         = path
		self.config       = config
		self.filename     = os.path.basename(self.path)
		self.dirname      = os.path.dirname(self.path)
		self.prev         = pprev
		self.next         = pnext
		self.thumb_path   = os.path.join(self.dirname, \
					'%s%s'%(config.get('photos', 'thumb_prefix'), self.filename))
		self.preview_path = os.path.join(self.dirname, \
					'%s%s'%(config.get('photos', 'preview_prefix'), self.filename))
		self.size         = Image.open(self.path).size
		self.width        = self.size[0]
		self.height       = self.size[1]
		self.is_square    = self.width == self.height
		self.is_vertical  = self.width < self.height 
		self.desc         = None
		self.title        = title or self.filename
		self.page         = None
		self.photodir     = config.get('album', 'photodir')
		self.href         = os.path.join(self.photodir, self.filename)
		self.preview      = os.path.join(self.photodir, os.path.basename(self.preview_path))
		self.thumb        = os.path.join(self.photodir, os.path.basename(self.thumb_path))

	def _extract_desc(self, default=''):
		descfile = self.path[:-3]+'desc'
		if os.path.exists(descfile):
			self.desc = codecs.open(descfile, 'rb', 'utf8').read().rstrip()
		else:
			self.desc = default

	def _get_size(self, height):
		return int(height * self.width / (self.height*1.0))

	def get_thumb_size(self):
		thumb_height = self.config.getint('photos', 'thumb_height')
		thumb_width  = self._get_size(thumb_height)
		return thumb_width, thumb_height

	def get_preview_size(self):
		preview_height = self.config.getint('photos', 'preview_height')
		preview_width  = self._get_size(preview_height)
		return preview_width, preview_height

def get_input(prompt):
	# python3 has no raw_input, and input has a potentially risky behaviour in python2. Try to fix that.
	if not 'raw_input' in dir(__builtins__):
		raw_input = input
	return raw_input(prompt)

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
	out = codecs.open('album.def', 'wb', 'utf8')
	out.write(base_template.format(**answers))
	out.close()

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

def build_index(site_config, recurse=False, build_albums=False, regen=False):
	try:
		albumset = AlbumSet(site_config, recurse, build_albums, regen)
		info ('Building directory index [{}]'.format(albumset.url))
		# FIXME: add option to specify output file name
		# albumset.render(output_file='index.test.html')
		albumset.render()
	except: # FIXME: what kind of exceptions do we expect?
		raise


if __name__ == '__main__':
	# Parse command line. FIXME: this needs to be properly documented
	parser = argparse.ArgumentParser()
	parser.add_argument('-v', '--verbose', action='store_true', help='Print more details about the ongoing task')
	parser.add_argument('-q', '--quiet', action='store_true', help="Don't display anything (except warnings and errors)")
	parser.add_argument('-r', '--recurse', action='store_true', help='Generate index files and albums for the entire subtree')
	parser.add_argument('-b', '--build-albums', action='store_true', help='Generate album files in the directory set')
	parser.add_argument('-f', '--force-regen', action='store_true', help='Force the regeneration of all album data')
	args = parser.parse_args()
	g_verbose = args.verbose
	g_quiet = args.quiet

	# Read the site config in the script main directory, and the album config in the current directory
	# The site config provides default values. All parameters can be overriden by the album config.
	# FIXME: this should probably be reworked to avoid writing a config in the script dir, but this will
	# FIXME: have to do for now.
	site_config = os.path.join(os.path.dirname(sys.argv[0]), 'site.config')


	# try generating an index first
	if os.path.exists('index.def'):
		build_index(site_config, recurse=args.recurse, build_albums=args.build_albums, regen=args.force_regen)
		sys.exit(0)

	# otherwise, deal with the album if there is one
	build_album(site_config, regen=args.force_regen, interactive=True)
