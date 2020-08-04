import os.path
import codecs

from PIL import Image

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

