import os, os.path
import re
import codecs
import configparser
import zipfile

from PIL import Image
from jinja2 import  Environment, FileSystemLoader
from tqdm import tqdm

from .photo import Photo
from .utils import info, verbose, error, warn, get_current_path
from .settings import settings

# Python2 does not know about FileNotFoundError, map it if needed
try:
	FileNotFoundError
except NameError:
	FileNotFoundError = IOError

# Helper function to crop a square image from a rectangle image
def _crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))

# Helper function to generate a square thumbnail from a large picture
def _gen_thumbnail(file_in, file_out, width=450):
	im = Image.open(file_in)
	im_thumb = _crop_center(im, min(im.size), min(im.size)).resize((width, width), Image.LANCZOS)
	im_thumb.save(file_out, quality=95)


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
			_gen_thumbnail(self.thumbnail_src, self.thumbnail, self.thumbnail_size)
			os.chmod(self.thumbnail, 0o644)
		prev = None
		verbose ("Generating thumbnails and preview images...")
		barfmt = '    |{bar}|{percentage:3.0f}% ({n_fmt}/{total_fmt}) [{elapsed}<{remaining}]'
		progress = tqdm(self._photos, ncols=80, position=0, bar_format=barfmt, leave=False, disable=settings.quiet)
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

