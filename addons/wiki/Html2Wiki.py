# Copyright (C) 2006 Samuel Abels, http://debain.org
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import HTMLParser, re, sys
from Cell import Cell

class Html2Wiki(HTMLParser.HTMLParser):
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.wiki       = ''
        self.buffer     = ''
        self.indent     = 0
        self.linebreak  = '\n'
        self.rows       = []
        self.cells      = []
        self.in_table   = False
        self.in_td      = False
        self.in_heading = False
        self.in_ul      = False
        self.in_ol      = False
        self.in_li      = False
        self.in_a       = False
        self.in_pre     = False
        self.last_href  = ''

    def __output(self, text, linebreak = True):
        self.buffer += (' ' * self.indent * 2)
        self.buffer += text + self.linebreak
        
    def __flush(self):
        self.wiki  += self.buffer
        self.buffer = ''
        
    def handle_starttag(self, tag, attrs):
        if   tag == 'table':  self.start_table()
        elif tag == 'tr':     self.start_tr()
        elif tag == 'th':     self.start_th(attrs)
        elif tag == 'td':     self.start_td(attrs)
        elif tag == 'h1':     self.start_h1()
        elif tag == 'h2':     self.start_h2()
        elif tag == 'h3':     self.start_h3()
        elif tag == 'ul':     self.start_ul()
        elif tag == 'ol':     self.start_ol()
        elif tag == 'li':     self.start_li()
        elif tag == 'i':      self.start_i()
        elif tag == 'b':      self.start_b()
        elif tag == 'u':      self.start_u()
        elif tag == 'a':      self.start_a(attrs)
        elif tag == 'pre':    self.start_pre()
        elif tag == 'strike': self.start_strike()
        elif tag == 'br':     self.newline()
        
    def handle_endtag(self, tag):
        if   tag == 'table':  self.end_table();
        elif tag == 'tr':     self.end_tr()
        elif tag == 'th':     self.end_th()
        elif tag == 'td':     self.end_td()
        elif tag == 'h1':     self.end_h1()
        elif tag == 'h2':     self.end_h2()
        elif tag == 'h3':     self.end_h3()
        elif tag == 'ul':     self.end_ul()
        elif tag == 'ol':     self.end_ol()
        elif tag == 'li':     self.end_li()
        elif tag == 'i':      self.end_i()
        elif tag == 'b':      self.end_b()
        elif tag == 'u':      self.end_u()
        elif tag == 'a':      self.end_a()
        elif tag == 'pre':    self.end_pre()
        elif tag == 'strike': self.end_strike()

    def start_h1(self):
        self.buffer += '='

    def end_h1(self):
        self.buffer += '=\n\n'

    def start_h2(self):
        self.buffer += '=='

    def end_h2(self):
        self.buffer += '==\n\n'

    def start_h3(self):
        self.buffer += '==='

    def end_h3(self):
        self.buffer += '===\n\n'

    def start_ul(self):
        self.in_ul = True

    def end_ul(self):
        self.in_ul = False

    def start_ol(self):
        self.in_ol = True

    def end_ol(self):
        self.in_ol = False

    def start_li(self):
        self.in_li = True
        if self.in_ol:
            self.buffer += '# '
        elif self.in_ul:
            self.buffer += '* '

    def end_li(self):
        self.in_li = False

    def start_i(self):
        self.buffer += '/'

    def end_i(self):
        self.buffer += '/'

    def start_b(self):
        self.buffer += '*'

    def end_b(self):
        self.buffer += '*'

    def start_u(self):
        self.buffer += '_'

    def end_u(self):
        self.buffer += '_'

    def start_a(self, attrs):
        self.in_a = True
        self.last_href = ''
        for key, value in attrs:
            if key == 'href':
                self.last_href = value
        self.buffer += '[' + self.last_href

    def end_a(self):
        self.in_a = False
        self.buffer += ']'

    def start_pre(self):
        self.in_pre = True
        self.buffer += '#Text\n'

    def end_pre(self):
        self.in_pre = False
        self.buffer += '#End\n'

    def start_strike(self):
        self.buffer += '-'

    def end_strike(self):
        self.buffer += '-'

    def start_table(self):
        self.in_table = True
        
    def start_tr(self):
        pass

    def start_th(self, attrs):
        self.in_heading = True
        self.start_td(attrs)

    def start_td(self, attrs):
        self.__flush()
        self.in_td = True
        cell       = Cell()
        for key, value in attrs:
            if key == 'rowspan':
                cell.rowspan = int(value)
            elif key == 'colspan':
                cell.colspan = int(value)
        self.cells.append(cell)

    def handle_data(self, data):
        if not self.in_pre:
            data = data.replace('\n', '')
        if self.in_a:
            if data == self.last_href:
                return
            self.buffer += ' '
        if self.in_li:
            self.buffer += data.strip() + '\n'
        if self.in_ul or self.in_ol:
            self.__flush()
        elif self.in_td:
            self.buffer += data
        elif not self.in_table:
            self.buffer += data
            self.__flush()

    def end_td(self):
        self.cells[-1].data += self.buffer.strip()
        self.buffer = ''
        self.in_td = False

    def end_th(self):
        self.end_td()

    def end_tr(self):
        if len(self.cells) is 0:
            return
        if self.in_heading:
            self.__output('#Heading')
            self.in_heading = False
        else:
            self.__output('#Row')
        self.indent += 1
        line = ('|' * self.cells[0].colspan) + ' ' + self.cells[0].data.strip()
        for cell in self.cells[1:]:
            line += ' ' + ('|' * cell.colspan) + ' ' + cell.data.strip()
        if len(line) <= 80:
            self.__output(line)
        else:
            for cell in self.cells:
                self.__output(('|' * cell.colspan) + ' ' + cell.data.strip())
        self.cells   = []
        self.indent -= 1
        self.__flush()

    def end_table(self):
        self.in_table = False
        self.__flush()

    def newline(self):
        self.buffer += '\n'


if __name__ == '__main__':
    import unittest
    import os
    from Wiki2Html import Wiki2Html

    class Wiki2HtmlTest(unittest.TestCase):
        def runTest(self):
            # Read the entire file into one string.
            filename = 'markup.txt'
            infile   = open(filename, 'r')
            in_str   = infile.read()
            infile.close()

            # Convert Wiki to HTML.
            parser = Wiki2Html()
            parser.read(filename)
            html1 = parser.html
            #print html1

            # Convert the HTML back to Wiki.
            parser = Html2Wiki()
            parser.feed(html1)
            wiki = parser.wiki
            #print wiki

            # Write the wiki to a file.
            # The result contains an extra newline to mark a table end.
            # This is generally ok, but would break the unit test, so we
            # remove the last character before writing.
            fd = open(filename + '.tmp', 'w')
            fd.write(wiki[:-1])
            fd.close()

            # Convert the new Wiki file to HTML again.
            parser = Wiki2Html()
            parser.read(filename + '.tmp')
            html2 = parser.html
            #print html2

            # Clean up.
            os.remove(filename + '.tmp')

            # Make sure that the model is complete.
            assert len(in_str) > 10
            assert len(html1)  > 10
            assert html1 == html2

    testcase = Wiki2HtmlTest()
    runner   = unittest.TextTestRunner()
    runner.run(testcase)
