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
import sys, string
sys.path.append('..')
from Plex import *

# Single char definitions.
letter      = Range('AZaz')
digit       = Range('09')
spaces      = Any(" \t\r\n")
nl          = Str("\n") | Eof
not_nl      = AnyBut("\r\n")
dash        = Str('-')
colon       = Str(':')
hash        = Str('#')
at          = Str('@')
equal       = Str('=')
star        = Str('*')
slash       = Str('/')
o_bracket   = Str('{')
c_bracket   = Str('}')
underscore  = Str('_')
dot         = Str('.')
punctuation = Any('.!?,;:')
quotes      = Any('\'"')

# Single word definitions.
name        = letter + Rep(letter | digit)
file_name   = Rep1(letter | digit | dash | underscore | dot)
wiki_force  = Str('->') + name
wiki_word   = Range('AZ') + name + Range('AZ') + name
not_w_word  = Str('!') + wiki_word
indentation = Rep(Str(' ')) | Rep(Str("\t"))
variable    = letter + Rep(letter | digit | Str('_')) + Rep(letter | digit)
proto       = Alt(Str('http'), Str('https'), Str('ftp'), Str('mailto'))
login       = file_name + Opt(colon + file_name)
host        = name + Rep(letter | digit | dash | underscore | dot) + name
path        = Opt(slash) + file_name + Rep(slash + file_name) + Opt(slash)
arg_value   = Rep1(letter | digit | dash | underscore | dot | Str('%'))
arg         = file_name + equal + Opt(arg_value)
args        = Str('?') + arg + Rep(Str('&') + arg)
path_args   = path + Opt(args)
url         = proto + colon + Str('//') + Opt(login + at) + host + Opt(path_args)
code        = Str('#Text') + nl
code_end    = Str('#End') + nl

# Markup.
line          = Rep(not_nl) + nl
blank_line    = indentation + nl
words         = Rep1(letter | digit | spaces)
list_item     = Bol + Alt(hash, star) + Str(' ')
italic_start  = Alt(Bol, spaces) + slash
italic_end    = slash + Alt(Eol, spaces, punctuation)
phrase        = Rep1(words | dash | at | punctuation | slash | quotes| hash | Str('$'))
title1        = equal + phrase + equal
title2        = equal + equal + phrase + equal + equal
title3        = equal + equal + equal + phrase + equal + equal + equal
heading       = Str('#Heading') + nl
row           = Str('#Row') + nl
cell          = Rep1(Str('|')) + Str(' ')
internal_link = Str('[') + url + Opt(spaces + phrase) + Str(']')
external_link = Str('[') + path_args + Opt(spaces + phrase) + Str(']')
image         = Str('Attach') + colon + Opt(phrase) + nl

class WikiParser(Scanner):
    def __init__(self, file, filename):
        Scanner.__init__(self, self.lexicon, file, filename)
        self.my_buffer             = ''
        self.indentation_stack     = [0]
        self.bracket_nesting_level = 0
        self.in_italic             = False
        self.in_bold               = False
        self.in_underline          = False
        self.in_list               = False
        self.in_list_item          = False
        self.in_table              = False
        self.in_heading            = False
        self.in_row                = False
        self.in_cell               = False
        self.begin('indent')

    def _buffer_flush(self):
        indent = self._get_current_indent_level()
        #print "_buffer_flush (%i): '%s'" % (indent, self.my_buffer)
        if self.my_buffer == '':
            return
        if self.my_buffer == '\n':
            self.produce('newline', '\n')
        else:
            self.produce('text', self.my_buffer)
        #print "Flush produced"
        self.my_buffer = ''

    def _newline_action(self, text):
        #print '_newline_action'
        self._buffer_flush()
        self.produce('newline', text)
        if self.bracket_nesting_level == 0:
            self.begin('indent')

    def _indentation_action(self, text):
        #print '_indentation_action'
        self.my_buffer += text
        self._buffer_flush()
        current_level = self._get_current_indent_level()
        new_level     = len(text)
        if new_level > current_level:
            self._indent_to(new_level)
        elif new_level < current_level:
            self._dedent_to(new_level)
        self.begin('')

    def _indent_to(self, new_level):
        self.indentation_stack.append(new_level)
        self.produce('indent', new_level)

    def _dedent_to(self, new_level):
        while new_level < self._get_current_indent_level():
            self.indentation_stack.pop()
        self.produce('dedent', self._get_current_indent_level())

    def _get_current_indent_level(self):
        return self.indentation_stack[-1]

    def _code_start(self, text):
        #print '_code_start: ' + text
        self._buffer_flush()
        self.produce('code_start', text)
        self.begin('code')

    def _code(self, text):
        #print '_code: ' + text
        self.my_buffer += text

    def _code_end(self, text):
        #print '_code_end: ' + text
        if self.my_buffer != '':
            self.produce('code', self.my_buffer)
            self.my_buffer = ''
        self.produce('code_end', text)
        self.begin('')

    def _title1(self, text):
        #print '_title1: ' + text
        self._buffer_flush()
        self.produce('title1_start', text[0])
        self.my_buffer += text[1:-1]
        self._buffer_flush()
        self.produce('title1_end', text[-1])

    def _title2(self, text):
        #print '_title2: ' + text
        self._buffer_flush()
        self.produce('title2_start', text[0:2])
        self.my_buffer += text[2:-2]
        self._buffer_flush()
        self.produce('title2_end', text[-2:])

    def _title3(self, text):
        #print '_title3: ' + text
        self._buffer_flush()
        self.produce('title3_start', text[0:3])
        self.my_buffer += text[3:-3]
        self._buffer_flush()
        self.produce('title3_end', text[-3:])

    def _italic_start(self, text):
        #print '_italic_start "%s"' % text
        if text[0] != '/':
            self.my_buffer += text[0]
        self._buffer_flush()
        self.in_italic = True
        self.produce('italic_start', text[-1])

    def _italic_end(self, text):
        #print '_italic_end'
        self._buffer_flush()
        self.produce('italic_end', text[0])
        self.in_italic = False
        self.my_buffer += text[1]

    def _bold(self, text):
        #print '_bold'
        self._buffer_flush()
        if self.in_bold:
            self.produce('bold_end', text)
            self.in_bold = False
        else:
            self.in_bold = True
            self.produce('bold_start', text)

    def _underline(self, text):
        #print '_underline'
        self._buffer_flush()
        if self.in_underline:
            self.produce('underline_end', text)
            self.in_underline = False
        else:
            self.in_underline = True
            self.produce('underline_start', text)

    def _list_item(self, text):
        self._buffer_flush()
        if not self.in_list:
            if text.startswith('#'):
                self.produce('numbered_list_start', '')
            elif text.startswith('*'):
                self.produce('unnumbered_list_start', '')
            self.in_list = True
        if self.in_list_item:
            self._list_item_end()
        self.in_list_item = True
        self.produce('list_item_start')
    
    def _list_item_end(self):
        self.in_list_item = False
        self.produce('list_item_end', '')

    def _list_end(self):
        if self.in_list_item:
            self._list_item_end()
        self.in_list = False
        self.produce('list_end', '')

    def _heading_start(self, text):
        self._buffer_flush()
        if not self.in_table:
            self.produce('table_start', '')
            self.in_table = True
        if self.in_heading:
            self._heading_end()
        self.in_heading = True
        self.produce('heading_start', text[:-1])
        self._newline_action(text[-1])

    def _row_start(self, text):
        self._buffer_flush()
        if not self.in_table:
            self.produce('table_start', '')
            self.in_table = True
        if self.in_heading:
            self._heading_end()
        if self.in_row:
            self._row_end()
        self.in_row = True
        self.produce('row_start', text[:-1])
        self._newline_action(text[-1])

    def _cell_start(self, text):
        self._buffer_flush()
        if not self.in_heading and not self.in_row:
            self._text(text)
            return
        if self.in_cell:
            self._cell_end()
        self.in_cell = True
        self.produce('cell_start')

    def _cell_end(self):
        self.in_cell = False
        self.produce('cell_end', '')

    def _row_end(self):
        if self.in_cell:
            self._cell_end()
        self.in_row = False
        self.produce('row_end', '')

    def _heading_end(self):
        if self.in_cell:
            self._cell_end()
        self.in_heading = False
        self.produce('heading_end', '')

    def _table_end(self):
        if self.in_heading:
            self._heading_end()
        if self.in_row:
            self._row_end()
        self.in_table = False
        self.produce('table_end', '')

    def _link(self, text):
        self._buffer_flush()
        self.produce('link', text)

    def _image(self, text):
        self._buffer_flush()
        self.produce('image', text)
        
    def _wiki_word(self, text):
        self._buffer_flush()
        self.produce('wiki_word', text)

    def _not_wiki_word(self, text):
        self._buffer_flush()
        self.produce('not_wiki_word_intro', text[0])
        self.produce('not_wiki_word', text[1:])

    def _open_bracket_action(self, text):
        #print '_open_bracket_action'
        self.my_buffer += text
        self.bracket_nesting_level = self.bracket_nesting_level + 1

    def _close_bracket_action(self, text):
        #print '_close_bracket_action'
        self.my_buffer += text
        self.bracket_nesting_level = self.bracket_nesting_level - 1

    def _blank_line(self, text):
        self._dedent_to(0)
        self.my_buffer += text
        if self.in_list:
            self._list_end()
        if self.in_table:
            self._table_end()
        self._buffer_flush()

    def _text(self, text):
        #print "Char: '%s'" % text
        self.my_buffer += text

    def eof(self):
        #print "EOF"
        self._blank_line('')

    lexicon = Lexicon([
        # Handle whitespace and indentation.
        (nl, _newline_action),
        State('indent', [
            (blank_line,  _blank_line),
            (indentation, _indentation_action)
        ]),

        # Preformatted text/code.
        (code,     _code_start),
        State('code', [
            (code_end, _code_end),
            (AnyChar,  _code)
        ]),

        # Brackets.
        (o_bracket, _open_bracket_action),
        (c_bracket, _close_bracket_action),

        # Styles.
        (list_item,    _list_item),
        (title1,       _title1),
        (title2,       _title2),
        (title3,       _title3),
        (star,         _bold),
        (underscore,   _underline),
        (italic_start, _italic_start),
        (italic_end,   _italic_end),

        # Tables.
        (heading, _heading_start),
        (row,     _row_start),
        (cell,    _cell_start),

        # Other.
        (internal_link, _link),
        (external_link, _link),
        (not_w_word,    _not_wiki_word),
        (wiki_word,     _wiki_word),
        (wiki_force,    _wiki_word),
        (AnyChar,       _text),
        (image,         _image)
    ])


if __name__ == '__main__':
    import unittest

    class ParserTest(unittest.TestCase):
        def runTest(self):
            # Read the entire file into one string.
            filename  = 'markup.txt'
            infile    = open(filename, "U")
            in_text   = infile.read()
            infile.close()

            # Re-open and parse the entire file.
            infile  = open(filename, "r")
            scanner = WikiParser(infile, filename)
            content = ''
            nonecount = 0
            while True:
                token    = scanner.read()
                position = scanner.position()
                if token[0] is None:
                    nonecount += 1  # This is because Plex is broken.
                if nonecount >= 2:
                    break
                #print "Token type: %s, Token: '%s'" % (token[0], token[1])
                if not token[0] in ['indent', 'dedent']:
                    content += token[1]

            # Make sure that every single string was extracted.
            #print content
            assert content == in_text

    testcase = ParserTest()
    runner   = unittest.TextTestRunner()
    runner.run(testcase)
