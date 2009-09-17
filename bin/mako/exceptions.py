# exceptions.py
# Copyright (C) 2006, 2007, 2008 Michael Bayer mike_mp@zzzcomputing.com
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""exception classes"""

import traceback, sys, re
from mako import util

class MakoException(Exception):
    pass

class RuntimeException(MakoException):
    pass

def _format_filepos(lineno, pos, filename):
    if filename is None:
        return " at line: %d char: %d" % (lineno, pos)
    else:
        return " in file '%s' at line: %d char: %d" % (filename, lineno, pos)     
class CompileException(MakoException):
    def __init__(self, message, source, lineno, pos, filename):
        MakoException.__init__(self, message + _format_filepos(lineno, pos, filename))
        self.lineno =lineno
        self.pos = pos
        self.filename = filename
        self.source = source
                    
class SyntaxException(MakoException):
    def __init__(self, message, source, lineno, pos, filename):
        MakoException.__init__(self, message + _format_filepos(lineno, pos, filename))
        self.lineno =lineno
        self.pos = pos
        self.filename = filename
        self.source = source
        
class TemplateLookupException(MakoException):
    pass

class TopLevelLookupException(TemplateLookupException):
    pass
    
class RichTraceback(object):
    """pulls the current exception from the sys traceback and extracts Mako-specific 
    template information.
    
    Usage:
    
    RichTraceback()
    
    Properties:
    
    error - the exception instance.  
    source - source code of the file where the error occured.  if the error occured within a compiled template,
    this is the template source.
    lineno - line number where the error occured.  if the error occured within a compiled template, the line number
    is adjusted to that of the template source
    records - a list of 8-tuples containing the original python traceback elements, plus the 
    filename, line number, source line, and full template source for the traceline mapped back to its originating source
    template, if any for that traceline (else the fields are None).
    reverse_records - the list of records in reverse
    traceback - a list of 4-tuples, in the same format as a regular python traceback, with template-corresponding 
    traceback records replacing the originals
    reverse_traceback - the traceback list in reverse
    
    """
    def __init__(self, traceback=None):
        (self.source, self.lineno) = ("", 0)
        (t, self.error, self.records) = self._init(traceback)
        if self.error is None:
            self.error = t
        if isinstance(self.error, CompileException) or isinstance(self.error, SyntaxException):
            import mako.template
            self.source = self.error.source
            self.lineno = self.error.lineno
            self._has_source = True
        self.reverse_records = [r for r in self.records]
        self.reverse_records.reverse()
    def _get_reformatted_records(self, records):
        for rec in records:
            if rec[6] is not None:
                yield (rec[4], rec[5], rec[2], rec[6])
            else:
                yield tuple(rec[0:4])
    traceback = property(lambda self:self._get_reformatted_records(self.records), doc="""
        return a list of 4-tuple traceback records (i.e. normal python format)
        with template-corresponding lines remapped to the originating template
    """)
    reverse_traceback = property(lambda self:self._get_reformatted_records(self.reverse_records), doc="""
        return the same data as traceback, except in reverse order
    """)
    def _init(self, trcback):
        """format a traceback from sys.exc_info() into 7-item tuples, containing
        the regular four traceback tuple items, plus the original template 
        filename, the line number adjusted relative to the template source, and
        code line from that line number of the template."""
        import mako.template
        mods = {}
        if not trcback:
            (type, value, trcback) = sys.exc_info()
        rawrecords = traceback.extract_tb(trcback)
        new_trcback = []
        for filename, lineno, function, line in rawrecords:
            try:
                (line_map, template_lines) = mods[filename]
            except KeyError:
                try:
                    info = mako.template._get_module_info(filename)
                    module_source = info.code
                    template_source = info.source
                    template_filename = info.template_filename or filename
                except KeyError:
                    new_trcback.append((filename, lineno, function, line, None, None, None, None))
                    continue

                template_ln = module_ln = 1
                line_map = {}
                for line in module_source.split("\n"):
                    match = re.match(r'\s*# SOURCE LINE (\d+)', line)
                    if match:
                        template_ln = int(match.group(1))
                    else:
                        template_ln += 1
                    module_ln += 1
                    line_map[module_ln] = template_ln
                template_lines = [line for line in template_source.split("\n")]
                mods[filename] = (line_map, template_lines)

            template_ln = line_map[lineno]
            if template_ln <= len(template_lines):
                template_line = template_lines[template_ln - 1]
            else:
                template_line = None
            new_trcback.append((filename, lineno, function, line, template_filename, template_ln, template_line, template_source))
        if not self.source:
            for l in range(len(new_trcback)-1, 0, -1):
                if new_trcback[l][5]:
                    self.source = new_trcback[l][7]
                    self.lineno = new_trcback[l][5]
                    break
            else:
                try:
                    # A normal .py file (not a Template)
                    fp = open(new_trcback[-1][0])
                    encoding = util.parse_encoding(fp)
                    fp.seek(0)
                    self.source = fp.read()
                    fp.close()
                    if encoding:
                        self.source = self.source.decode(encoding)
                except IOError:
                    self.source = ''
                self.lineno = new_trcback[-1][1]
        return (type, value, new_trcback)

                
def text_error_template(lookup=None):
    """provides a template that renders a stack trace in a similar format to the Python interpreter,
    substituting source template filenames, line numbers and code for that of the originating
    source template, as applicable."""
    import mako.template
    return mako.template.Template(r"""
<%page args="traceback=None"/>
<%!
    from mako.exceptions import RichTraceback
%>\
<%
    tback = RichTraceback(traceback=traceback)
%>\
Traceback (most recent call last):
% for (filename, lineno, function, line) in tback.traceback:
  File "${filename}", line ${lineno}, in ${function or '?'}
    ${line | unicode.strip}
% endfor
${str(tback.error.__class__.__name__)}: ${str(tback.error)}
""")

def html_error_template():
    """provides a template that renders a stack trace in an HTML format, providing an excerpt of 
    code as well as substituting source template filenames, line numbers and code 
    for that of the originating source template, as applicable.

    the template's default encoding_errors value is 'htmlentityreplace'. the template has
    two options:

    with the full option disabled, only a section of an HTML document is returned.
    with the css option disabled, the default stylesheet won't be included."""
    import mako.template
    return mako.template.Template(r"""
<%!
    from mako.exceptions import RichTraceback
%>
<%page args="full=True, css=True, traceback=None"/>
% if full:
<html>
<head>
    <title>Mako Runtime Error</title>
% endif
% if css:
    <style>
        body { font-family:verdana; margin:10px 30px 10px 30px;}
        .stacktrace { margin:5px 5px 5px 5px; }
        .highlight { padding:0px 10px 0px 10px; background-color:#9F9FDF; }
        .nonhighlight { padding:0px; background-color:#DFDFDF; }
        .sample { padding:10px; margin:10px 10px 10px 10px; font-family:monospace; }
        .sampleline { padding:0px 10px 0px 10px; }
        .sourceline { margin:5px 5px 10px 5px; font-family:monospace;}
        .location { font-size:80%; }
    </style>
% endif
% if full:
</head>
<body>
% endif

<h2>Error !</h2>
<%
    tback = RichTraceback(traceback=traceback)
    src = tback.source
    line = tback.lineno
    if src:
        lines = src.split('\n')
    else:
        lines = None
%>
<h3>${str(tback.error.__class__.__name__)}: ${str(tback.error)}</h3>

% if lines:
    <div class="sample">
    <div class="nonhighlight">
% for index in range(max(0, line-4),min(len(lines), line+5)):
    % if index + 1 == line:
<div class="highlight">${index + 1} ${lines[index] | h}</div>
    % else:
<div class="sampleline">${index + 1} ${lines[index] | h}</div>
    % endif
% endfor
    </div>
    </div>
% endif

<div class="stacktrace">
% for (filename, lineno, function, line) in tback.reverse_traceback:
    <div class="location">${filename}, line ${lineno}:</div>
    <div class="sourceline">${line | h}</div>
% endfor
</div>

% if full:
</body>
</html>
% endif
""", output_encoding=sys.getdefaultencoding(), encoding_errors='htmlentityreplace')
