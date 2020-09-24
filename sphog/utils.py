from __future__ import print_function
import sys
import os
from .settings import settings

# Helper functions to report the script status.
# note: python logging seems a little overkill for our needs, so we don't use it
def verbose(message):
	if settings.verbose == True and settings.quiet == False:
		print (u'    | {}'.format(message))

def info(message):
	if settings.info == True and settings.quiet == False:
		print (u'I: {}'.format(message))

def warn(message):
	print (u'W: {}'.format(message), file=sys.stderr)

def error(message):
	print (u'E: {}'.format(message), file=sys.stderr)



# Python2 os.getcwd returns ascii paths, we need unicode
def get_current_path():
	try:
		# python2: call getcwdu()
		path = os.getcwdu()
	except AttributeError:
		# python3 returns unicode by default
		path = os.getcwd()
	return path
