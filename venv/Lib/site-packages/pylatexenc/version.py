#
# The MIT License (MIT)
# 
# Copyright (c) 2021 Philippe Faist
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#


#
# Self-note: Checklist
#
#   1) First some checks:
#
#       - Set below in this file ' version_str = "X.Xb" ' (beta version for next
#         release) for the following tests.
#
#       - tests pass: https://travis-ci.org/github/phfaist/pylatexenc
#
#       - LGTM looks good: https://lgtm.com/projects/g/phfaist/pylatexenc/
#
#       - python package creation works: (python setup.py sdist, pip install
#         dist/pylatexenc-xxx.tar.gz)
#
#   2) update change log (doc/changes.rst)
#
#   3) bump version number here
#
#   4) git commit any remaining changes
#
#   5) " git tag vX.X -am '<message>' "
#
#   6) " git push && git push --tags "
#
#   7) on github.com, fill in release details with a summary of changes etc.
#
#   8) create the source package for PyPI (" python3 setup.py sdist ")
#   
#   8) upload package to PyPI (twine upload dist/pylatexenc-X.X.tar.gz -r realpypi)
#

version_str = "2.10"
