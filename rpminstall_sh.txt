#
# This file is used by 'python setup.py bdist_rpm'
# You should not execute/call this file yourself.
#
# This script is used as the 'install' part of the RPM .spec file.
#
# Need to overwrite the install-part of the RPM to append the
# compression-suffix onto the filenames for the man-pages.
#
python -c "import compileall, os; compileall.compile_dir(os.path.join(os.environ['PWD'], 'doc'), force=True)"
python -O -c "import compileall, os; compileall.compile_dir(os.path.join(os.environ['PWD'], 'doc'), force=True)"
python setup.py install --optimize 1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

SUFFIX=gz
sed "s!\(/share/man/.*\)!\1.$SUFFIX!" -i INSTALLED_FILES
