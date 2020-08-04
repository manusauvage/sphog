class Settings(object):
	def __init__(self):
		self._verbose = False
		self._info = True
		self._quiet = False

	@property
	def verbose(self):
		return self._verbose

	@verbose.setter
	def verbose(self, value):
		self._verbose = value

	@property
	def info(self):
		return self._info

	@info.setter
	def info(self, value):
		self._info = value

	@property
	def quiet(self):
		return self._quiet

	@quiet.setter
	def quiet(self, value):
		self._quiet = value

# instanciate a settings object with default value, 
# which can be used (and updated) globally
settings = Settings()
