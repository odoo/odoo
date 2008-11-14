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
from WikiParser import WikiParser
from cgi        import escape

class Wiki2Html:
    def __init__(self):
        self.html              = ''
        self.buffer            = ''
        self.counter           = 0
        self.in_list           = False
        self.in_numbered_list  = False
        self.in_heading        = False
        self.in_table          = False
        self.in_cell           = False
        self.indent_level      = 0
        self.url_handler       = None
        self.wiki_word_handler = None


    def set_url_handler(self, handler):
        """
        Whenever the parser finds a URL in the output, by default it
        automatically translates it into a clickable link in the HTML output.
        However, if you want more fine-grained control over which URLs are
        converted into links, you might want to use this function.
        It calls the given handler function before a link is added into the
        HTML. The function is passed the URL and the caption.
        The handler can the modify the URL and the caption, and pass it
        back to the parser. Example handler:
        
        def url_handler(url, caption):
            return (url, 'My Caption')
        
        The parser uses the returned values to build a link in the HTML.
        If URL is None, the item is not linked at all.
        """
        self.url_handler = handler


    def set_wiki_word_handler(self, handler):
        """
        Like set_url_handler() but for WikiWords.
        Example handler:
        
        def wiki_word_handler(word):
            return (url, word)
        
        The parser uses the returned values to build a link in the HTML.
        If URL is None, the item is not linked at all.
        """
        self.wiki_word_handler = handler

    #onclick="openWindow(getURL('/attachment', {model: 'base.wiki', id: id=$id}), {name : 'Attachments'})
    def image(self, text):
        image = text.strip()
        url = image.split(':')[1]
        self.buffer += """<a href="/wiki/fullScreen?file='"""+ url +"""'&amp;id=$id">
            <img height='50%' alt='Please upload Image' width='60%' src="/wiki/getImage?file='"""+ url +"""'&amp;model='base.wiki'&amp;id=$id"/></a><br/>\n"""
        
    def indent(self, level):
        self.indent_level = level

    def dedent(self, level):
        self.indent_level = level


    def code_start(self, text):
        self.buffer += '<pre>'


    def code(self, text):
        self.buffer += escape(text)


    def code_end(self, text):
        self.buffer += '</pre>\n'


    def title1_start(self, text):
        self.buffer += '<h1>'


    def title1_end(self, text):
        self.buffer += '</h1>'


    def title2_start(self, text):
        self.buffer += '<h2>'


    def title2_end(self, text):
        self.buffer += '</h2>'


    def title3_start(self, text):
        self.buffer += '<h3>'


    def title3_end(self, text):
        self.buffer += '</h3>'


    def italic_start(self, text):
        self.buffer += '<i>'


    def italic_end(self, text):
        self.buffer += '</i>'


    def bold_start(self, text):
        self.buffer += '<b>'


    def bold_end(self, text):
        self.buffer += '</b>'


    def underline_start(self, text):
        self.buffer += '<u>'


    def underline_end(self, text):
        self.buffer += '</u>'


    def unnumbered_list_start(self, text):
        self.buffer += '<ul>\n'
        self.in_list = True


    def numbered_list_start(self, text):
        self.buffer += '<ol>\n'
        self.in_list = True
        self.in_numbered_list = True


    def list_end(self, text):
        if self.in_numbered_list:
            self.buffer += '</ol>\n'
            self.in_numbered_list = False
        else:
            self.buffer += '</ul>\n'
        self.in_list = False


    def list_item_start(self, text):
        self.buffer += '<li>'


    def list_item_end(self, text):
        self.__flush(True)
        self.buffer += '</li>\n'


    def table_start(self, text):
        self.in_table = True
        self.counter  = 0
        self.buffer += '<table>\n'


    def heading_start(self, text):
        self.in_heading = True
        self.row_start(text)


    def row_start(self, text):
        self.buffer  += '<tr>'


    def cell_start(self, text):
        self.in_cell = True
        attribs = ''
        if len(text) - 1 > 1:
            attribs += ' colspan=%i' % (len(text) - 1)
        if self.in_heading:
            self.buffer += '<th%s>' % attribs
        else:
            self.buffer += '<td%s>' % attribs
        self.__flush(True)


    def cell_end(self, text):
        # If the cell contains only a hash, replace it by a counter.
        if self.buffer.strip() == '#':
            self.counter += 1
            self.buffer = str(self.counter) + '.'
        self.__flush(True)
        self.in_cell = False
        if self.in_heading:
            self.html += '</th>'
        else:
            self.html += '</td>'
        self.html += '\n' + (' ' * self.indent_level)


    def row_end(self, text):
        self.buffer += '</tr>\n' + (' ' * self.indent_level)


    def heading_end(self, text):
        self.in_heading = False
        self.row_end(text)


    def table_end(self, text):
        self.in_table = False
        self.buffer += '</table>\n'


    def text(self, text):
        self.buffer += escape(text).replace('\n', '<br/>\n')


    def newline(self, text):
        if (self.in_table
            or self.in_list
            or (self.buffer[-5:-2] == '</h' and self.buffer[-1] == '>')
            or (self.buffer[-6:-3] == '</h' and self.buffer[-2] == '>')):
            self.buffer += '\n'
            return
        self.buffer += '<br/>\n'


    def link(self, text):
        text = text[1:-1]
        pos = text.find('-')
        if pos == -1:
            url     = text
            caption = url
        else:
            url     = text[:pos]
            caption = text[pos + 1:]
        if self.url_handler is not None:
            (url, caption) = self.url_handler(url.strip()+"'", caption)
        url     = escape(url)
        caption = escape(caption)
        if url is None:
            self.buffer += caption
        else:
            if url.strip().startswith('http') or url.strip().startswith('www') or url.strip().startswith('https') or url.strip().startswith('frp'):
                self.buffer += '<a href="%s" target="blank">%s</a>' % (url.strip(), caption)
            else:
                self.buffer += '<a href="%s">%s</a>' % ("/wiki?id="+url.strip()+"&amp;title='" + caption.strip() + "'" , caption )

    def wiki_word(self, text):
        if text.startswith('->'):
            text = text[2:]
        url     = text
        caption = text
        if self.wiki_word_handler is not None:
            (url, caption) = self.wiki_word_handler("/wiki?id='"+url.strip()+"'", caption)
        url     = escape(url)
        caption = escape(caption)
        if url is None:
            self.buffer += caption
        else:
            self.buffer += '<a href="%s">%s</a>' % ("/wiki?id='"+url.strip()+"'", caption)


    def not_wiki_word(self, text):
        self.buffer += escape(text)


    def __flush(self, strip = False):
        if strip:
            self.html += self.buffer.strip()
        else:
            self.html += self.buffer
        self.buffer = ''


    def read(self, filename):
        infile    = open(filename, 'U')
        parser    = WikiParser(infile, filename)
        nonecount = 0
        self.html = ''
        while True:
            token    = parser.read()
            position = parser.position()
            if token[0] is None:
                nonecount += 1  # This is because Plex is broken.
            if nonecount >= 2:
                break
            try:
                method = getattr(self, token[0])
            except:
                method = None
            if method is not None:
                method(token[1])
        infile.close()
        self.__flush()


if __name__ == '__main__':
    import unittest

    class Wiki2HtmlTest(unittest.TestCase):
        def runTest(self):
            # Read the entire file into one string.
            filename = 'markup.txt'
            infile   = open(filename, 'r')
            in_str   = infile.read()
            infile.close()

            # Parse the file.
            parser = Wiki2Html()
            parser.read(filename)
            html = parser.html
            print html

            # Now *that's* a poor test, huh? For a better test, look
            # at the test in Html2Wiki.py.
            assert len(html) > 1000

    testcase = Wiki2HtmlTest()
    runner   = unittest.TextTestRunner()
    runner.run(testcase)
