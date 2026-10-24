
"""
Module to expose more detailed version info for the installed `numpy`
"""
version = "2.4.0"
__version__ = version
full_version = version

git_revision = "c5ab79c14c98bfda1e60770ffa23a6130f8267b7"
release = 'dev' not in version and '+' not in version
short_version = version.split("+")[0]
