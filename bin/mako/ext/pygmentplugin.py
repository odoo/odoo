import re
try:
    set
except NameError:
    from sets import Set as set

from pygments.lexers.web import \
     HtmlLexer, XmlLexer, JavascriptLexer, CssLexer
from pygments.lexers.agile import PythonLexer
from pygments.lexer import Lexer, DelegatingLexer, RegexLexer, bygroups, \
     include, using, this
from pygments.token import Error, Punctuation, \
     Text, Comment, Operator, Keyword, Name, String, Number, Other, Literal
from pygments.util import html_doctype_matches, looks_like_xml

class MakoLexer(RegexLexer):
    name = 'Mako'
    aliases = ['mako']
    filenames = ['*.mao']

    tokens = {
        'root': [
            (r'(\s*)(\%)(\s*end(?:\w+))(\n|\Z)',
             bygroups(Text, Comment.Preproc, Keyword, Other)),
            (r'(\s*)(\%)([^\n]*)(\n|\Z)',
             bygroups(Text, Comment.Preproc, using(PythonLexer), Other)),
             (r'(\s*)(##[^\n]*)(\n|\Z)',
              bygroups(Text, Comment.Preproc, Other)),
              (r'''(?s)<%doc>.*?</%doc>''', Comment.Preproc),
            (r'(<%)([\w\.\:]+)', bygroups(Comment.Preproc, Name.Builtin), 'tag'),
            (r'(</%)([\w\.\:]+)(>)', bygroups(Comment.Preproc, Name.Builtin, Comment.Preproc)),
            (r'<%(?=([\w\.\:]+))', Comment.Preproc, 'ondeftags'),
            (r'(<%(?:!?))(.*?)(%>)(?s)', bygroups(Comment.Preproc, using(PythonLexer), Comment.Preproc)),
            (r'(\$\{)(.*?)(\})',
             bygroups(Comment.Preproc, using(PythonLexer), Comment.Preproc)),
            (r'''(?sx)
                (.+?)               # anything, followed by:
                (?:
                 (?<=\n)(?=%|\#\#) |  # an eval or comment line
                 (?=\#\*) |          # multiline comment
                 (?=</?%) |         # a python block
                                    # call start or end
                 (?=\$\{) |         # a substitution
                 (?<=\n)(?=\s*%) |
                                    # - don't consume
                 (\\\n) |           # an escaped newline
                 \Z                 # end of string
                )
            ''', bygroups(Other, Operator)),
            (r'\s+', Text),
        ],
        'ondeftags': [
            (r'<%', Comment.Preproc),
            (r'(?<=<%)(include|inherit|namespace|page)', Name.Builtin),
            include('tag'),
        ],
        'tag': [
            (r'((?:\w+)\s*=)\s*(".*?")',
             bygroups(Name.Attribute, String)),
            (r'/?\s*>', Comment.Preproc, '#pop'),
            (r'\s+', Text),
        ],
        'attr': [
            ('".*?"', String, '#pop'),
            ("'.*?'", String, '#pop'),
            (r'[^\s>]+', String, '#pop'),
        ],
    }


class MakoHtmlLexer(DelegatingLexer):
    name = 'HTML+Mako'
    aliases = ['html+mako']

    def __init__(self, **options):
        super(MakoHtmlLexer, self).__init__(HtmlLexer, MakoLexer,
                                              **options)

class MakoXmlLexer(DelegatingLexer):
    name = 'XML+Mako'
    aliases = ['xml+mako']

    def __init__(self, **options):
        super(MakoXmlLexer, self).__init__(XmlLexer, MakoLexer,
                                             **options)

class MakoJavascriptLexer(DelegatingLexer):
    name = 'JavaScript+Mako'
    aliases = ['js+mako', 'javascript+mako']

    def __init__(self, **options):
        super(MakoJavascriptLexer, self).__init__(JavascriptLexer,
                                                    MakoLexer, **options)

class MakoCssLexer(DelegatingLexer):
    name = 'CSS+Mako'
    aliases = ['css+mako']

    def __init__(self, **options):
        super(MakoCssLexer, self).__init__(CssLexer, MakoLexer,
                                             **options)
