# sphog - Simple Photo Gallery
A simple tool to quickly generate static photo galleries.


# Description
This script relies on [PIL](http://www.pythonware.com/products/pil/) for image processing and [jinja2](https://palletsprojects.com/p/jinja/) for templates. It has been built for Python 3.x, but it should work well with Python 2.7 as well.

# Usage
The script can be launched from an album directory (containing pictures), or from an index directory (containing album directories or index subdirectories):
```
% sphog.py --help
sphog.py [-h] [-v] [-q] [-r] [-b] [-f]

optional arguments:
  -h, --help          show this help message and exit
  -v, --verbose       Print more details about the ongoing task
  -q, --quiet         Don't display anything (except warnings and errors)
  -r, --recurse       Generate index files and albums for the entire subtree
  -b, --build-albums  Generate album files in the directory set
  -f, --force-regen   Force the regeneration of all album data
%
```

If the current directory contains an `album.def` file (see documentation for syntax), a new album will be generated automatically:
```
% ls -l
total 8
-rw------- 1 user group   93 Jul 21 12:15 album.def
drwxr-xr-x 2 user group 4096 Jul 22 12:56 photos
% cat album.def
[album]
title: Nice photos
desc: Taken with love and a digital camera
date: Sometime in 2009
% sphog.py --verbose
I: Building album [/misc/test_album/]
    | Generating album thumbnail (vignette.jpg)
    | Generating thumbnails and preview images...
% ls -l
total 84
-rw------- 1 user group    93 Jul 21 12:15 album.def
-rw-r--r-- 1 user group  2347 Jul 22 12:59 index.html
drwxr-xr-x 2 user group  4096 Jul 22 12:59 photos
-rw-r--r-- 1 user group 72302 Jul 22 12:59 vignette.jpg
```

# Documentation
## Configuration files
`album.def` and `index.def`
TODO: document format

## Default templates
Default templates are provided. They leverage the following js libs:
- [jQuery](https://jquery.com/) - versions 1, 2 & 3 should be supported
- [Magnific-Popup](https://github.com/manusauvage/Magnific-Popup) (patched version to support jQuery3)
- [jquery-collagePlus](https://github.com/ed-lea/jquery-collagePlus)


## Creating custom templates 
### Album templates
When an album template is rendered, it can us all data exposed by an `Album` object and from the collection of `Photo` objects found in that `Album`.

Useful `Album` properties include:
- `name` - the title of the album
- `desc` - the long description of the album
- `date` - information that can be used to date the album (this is a free form string, not a `datetime` object)
- `archive` - the path to the photo archive (a zip file) which may be generated
- `stylesheet` - a link to the stylesheet used to render the album
- `photodir` - the path where photos are stored (default: `photos/`)  
- `count` - the number of photos in the album
- `url` - the default URL for the album
- `parent` - the URL for the album parent index

Iterating on an `Album` object yields the individual `Photo` objects composing it.

Useful `Photo` properties include:
- `title` - the title of the photo
- `desc` - the long description of the photo
- `width` - the image width (full resolution)
- `height` - the image height (full resolution)
- `filename` - the filename of the actual image (full resolution)
- `href` - the path to the actual image (full resolution)
- `thumb` - the path to the smaller image thumbnail (e.g. used to create the image grid)
- `preview` - the path to the standard image (large enough to quickly browse through the images)
- `is_square` - a boolean flag indicating if the image is square or not
- `is_vertical` - a boolean flag indicating whether the image height is larger than the image width

### Index templates
TODO: document

# Examples of generated galleries
Example galleries can be found [here](http://photos.lechevoir.net/public/)
