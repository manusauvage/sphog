import os
import os.path
import re
import configparser
import codecs

from jinja2 import  Environment, FileSystemLoader

from .album import Album
from .utils import get_current_path

# Python2 does not know about FileNotFoundError, map it if needed
try:
	FileNotFoundError
except NameError:
	FileNotFoundError = IOError

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

