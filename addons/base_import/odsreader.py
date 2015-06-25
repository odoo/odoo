#!/usr/bin/python
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
import xml.parsers.expat
import zipfile

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class odsreader:
    def __init__(self, file):

        xmldata = zipfile.ZipFile(StringIO(file)).read('content.xml')

        self.__rows = []
        self.__working_row = []

        p = xml.parsers.expat.ParserCreate()

        p.StartElementHandler = self.__start_element__
        p.EndElementHandler = self.__end_element__
        p.CharacterDataHandler = self.__char_data__
        # parse the data
        p.Parse(xmldata, True)

    def __iter__(self):
        return iter(self.__rows)

    def __start_element__(self, name, attrs):
        if name == 'table:table-row':
            self.__working_row = []

    def __end_element__(self, name):
        if name == 'table:table-row' and len(self.__working_row) > 0:
            self.__rows.append(self.__working_row)

    def __char_data__(self, data):
        self.__working_row.append(data)
