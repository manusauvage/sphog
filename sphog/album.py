# encoding: utf-8

'''
Implementation of the Album class and its associated helper functions.
'''

import os
import os.path
import re
import codecs
import configparser
import zipfile

from PIL import Image, ExifTags
from jinja2 import  Environment, FileSystemLoader
from tqdm import tqdm

from .photo import Photo
from .utils import verbose, error, warn, get_current_path
from .settings import settings

# Python2 does not know about FileNotFoundError, map it if needed
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

def _crop_center(pil_img, crop_width, crop_height):
    '''Helper function to crop a square image from a rectangle image'''
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))

def _gen_thumbnail(file_in, file_out, width=450):
    '''
    Helper function to generate a square thumbnail from a large picture
    '''
    try:
        im = Image.open(file_in)
        im_thumb = _crop_center(
            im,
            min(im.size),
            min(im.size)
            ).resize((width, width), Image.LANCZOS)
        im_thumb.save(file_out, quality=95)
        return True
    except FileNotFoundError:
        error('Could not find thumbnail source [{}]'.format(file_in))
        return False


def _gen_image_copy(path_in, path_out, size):
    '''
    Helper function to generate a smaller version of a photo
    (e.g. thumbnails, preview)
    '''
    thumb = Image.open(path_in)
    rotation = 0
    # FIXME: use PIL.Image.Exif instead of private method
    if thumb._getexif():
        # extract EXIF metadata and check whether we need to rotate
        # the output file. PIL does not copy metadata, and we don't
        # want to lose the orientation.
        exif = dict((ExifTags.TAGS[k], v) for k, v in thumb._getexif().items() if k in ExifTags.TAGS)
        if 'Orientation' in exif:
            o = exif['Orientation']
            if o == 8: rotation = 90
            if o == 3: rotation = 180
            if o == 6: rotation = 270
            if o in (8, 6):
                # swap height and width when rotation is 90 or 270
                rsize = (size[1], size[0])
                size = rsize
    if rotation > 0:
        # Rotate the resized image when needed
        verbose ('{} needs rotation: {}°'.format(path_in, rotation))
        thumb = thumb.rotate(rotation, expand=True)
    # Resize the photo to match the expected size.
    thumb = thumb.resize(size, Image.ANTIALIAS)
    thumb.save(path_out)
    os.chmod(path_out, 0o644)



class Album(object):
    '''
    The Album class handles all the required data associated with an album
    definition. It stores the album properties, the list of photos, and the
    various paths required to interact with the album. It also implements
    the rendering code, using jinja2 templates.
    '''
    def __init__(self, site_config, regen=False):
        # FIXME: Album config file is hardcoded, but this is a tough one:
        # FIXME: at some point we need a file to hold our properties.
        # FIXME: This might be solved by specifying the path in site_config,
        # FIXME: but this would not be a major improvement
        # FIXME: (and it would need two config reads.)
        album_config = 'album.def'
        if not os.path.isfile(album_config):
            raise FileNotFoundError(
                'E: Could not read {} file'.format(album_config)
                )
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
        self.base       = u'/{}/'.format(
            self.path.replace(
                config.get('global', 'siteroot'),
                ''
                )
            ).replace('//', '/')
        self.url        = self.base
        self.regen      = regen
        if self.url[-1] == '/': self.url = self.url[:-1]
        try:
            self.parent  = config.get('album', 'parent')
        except configparser.NoOptionError:
            self.parent = self._get_parent()
        self._photos = []

    def __iter__(self):
        '''Make the Album objects iterable'''
        for p in sorted(self._photos, key=lambda p: p.filename):
            yield p

    def add(self, photo):
        photo.config = self.config
        self._photos.append(photo)
        self.count += 1

    def _get_parent(self):
        '''Returns the path to the parent directory'''
        parent = os.path.abspath(os.path.join(self.path, os.pardir))
        siteroot = self.config.get('global', 'siteroot')
        return u'{}'.format(
            re.sub(r'^{}'.format(siteroot), '/', parent)
            ).replace('//', '/')

    def _parse_photodir(self):
        '''Parses `album.photodir` to find photos'''
        # parse album.photodir to find original photos and add them to
        # the object's list
        for dirname, dirnames, filenames in os.walk(self.photodir):
            del dirname, dirnames  # unused
            for f in filenames:
                if not re.match(r'\.jpg', f[-4:], re.I):
                    continue
                thumb   = self.config.get('photos', 'thumb_prefix')
                preview = self.config.get('photos', 'preview_prefix')
                if re.match('^(%s|%s)'%(thumb, preview), f):
                    continue
                # Only consider photos located directly in photodir,
                # ignore subdirs
                if os.path.exists(os.path.join(self.photodir, f)):
                    self.add(
                        Photo(
                            os.path.join(self.photodir, f),
                            self.config
                            )
                        )

    def _zip_files(self):
        '''Creates a Zip archive from album data'''
        if os.path.exists(self.archive):
            if self.regen is False:
                verbose(
                    'zip archive {} already created'.format(self.archive)
                    )
                return
            else:
                verbose(
                    'Removing existing zip archive [{}]'.format(self.archive)
                    )
                os.remove(self.archive)
        verbose ('Creating zip archive...')
        with zipfile.ZipFile(self.archive, 'w') as z:
            for p in self._photos:
                z.write(p.path)
        os.chmod(self.archive, 0o644)

    def prepare(self):
        '''
        Prepares the album by creating and building the required elements
        '''
        self._photos = []
        self.count = 0
        self._parse_photodir()
        # now we have the list of original photos, generate thumbnails
        # and preview, if needed
        self._photos = sorted(self._photos, key=lambda p: p.filename)
        # If no photo has been designated as a source for the album picture,
        # take the first one that comes
        if self.thumbnail_src == '' and len(self._photos) > 0:
            self.thumbnail_src = self._photos[0].path
        if not os.path.isfile(self.thumbnail) or self.regen is True:
            verbose(
                u'Generating album thumbnail ({})'.format(self.thumbnail)
                )
            if _gen_thumbnail(
                    self.thumbnail_src,
                    self.thumbnail,
                    self.thumbnail_size
                    ):
                os.chmod(self.thumbnail, 0o644)
            elif len(self._photos) > 0:
                warn(u'Using first picture as album thumbnail')
                if _gen_thumbnail(
                         self._photos[0].path,
                         self.thumbnail,
                         self.thumbnail_size
                         ):
                    os.chmod(self.thumbnail, 0o644)
            else:
                warn(
                    'No picture found in album, '
                    'skipping thumbnail generation'
                    )
        prev = None
        verbose ('Generating thumbnails and preview images...')
        barfmt = (
            '    '
            '|{bar}|{percentage:3.0f}% '
            '({n_fmt}/{total_fmt}) '
            '[{elapsed}<{remaining}]'
            )
        progress = tqdm(
            self._photos,
            ncols=80,
            position=0,
            bar_format=barfmt,
            leave=False,
            disable=settings.quiet
            )
        for p in progress:
            os.chmod(p.path, 0o644)
            # p._extract_desc(default=self.desc)
            p._extract_desc()
            if not os.path.exists(p.thumb_path) or self.regen is True:
                _gen_image_copy(p.path, p.thumb_path, p.get_thumb_size())
            if not os.path.exists(p.preview_path) or self.regen is True:
                _gen_image_copy(p.path, p.preview_path, p.get_preview_size())
            if prev:
                prev.next = p
            p.prev = prev
            prev = p
        # Create an archive containing the original photos, if requested
        if self.archive != '':
            self._zip_files()

    def render(self, output_file='index.html'):
        '''
        Renders current album using the appropriate template.
        FIXME: Output file is hardcoded to index.html, maybe this should change
        '''
        env = Environment(
            loader=FileSystemLoader(
                searchpath=self.config.get('global', 'templatedir')
                )
            )
        template = env.get_template(self.template)
        with codecs.open(output_file, 'wb', 'utf8') as out:
            tmp_output = template.render(album=self)
            out.write(tmp_output)
        os.chmod(output_file, 0o644)
