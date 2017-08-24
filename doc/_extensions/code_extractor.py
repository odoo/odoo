# -*- coding: utf-8 -*-
import codecs
import collections
import itertools
import os
import os.path
import stat
import re

import cStringIO
import textwrap

from docutils import nodes
from docutils.parsers.rst import directives
from pygments.lexers import get_lexer_by_name
from sphinx.builders import Builder
from sphinx.directives.code import CodeBlock
from sphinx.util.nodes import set_source_info

def setup(app):
    app.add_directive('snippet', SnippetDirective)
    app.add_builder(ExtractorBuilder)


class SnippetDirective(CodeBlock):
    """
    * hide: whether the snippet should be hidden in non-extracted output 
            (e.g. html). It is always extracted
    * indent: snippets are always dedented during extraction. Can be either a
              number of spaces to indent by, or a string to indent with (e.g. 
              a line comment)
    """
    option_spec = {
        'indent': directives.unchanged,
        'hide': directives.flag,
        # CodeBlock options
        'linenos': directives.flag,
        'lineno-start': int,
        'emphasize-lines': directives.unchanged_required,
        'class': directives.class_option,
        'name': directives.unchanged,
    }

    def run(self):
        if 'hide' in self.options:
            code = '\n'.join(self.content)
            node = nodes.comment(
                code, code,
                language=self.arguments[0],
                snippet=True,
                indent=self.options.get('indent', ''),
            )
            set_source_info(self, node)
            return [node]

        [node] = super(SnippetDirective, self).run()
        if isinstance(node, nodes.system_message):
            return [node]
        # ensure this was not a captioned block (not handling that currently)
        assert isinstance(node, nodes.literal_block), "snippets should not be captioned"
        node['snippet'] = True
        node['indent'] = self.options.get('indent', '')
        return [node]

ext_pattern = re.compile(r'\*\.\w+')
class ExtractorBuilder(Builder):
    name = 'extractor'

    def write(self, build_docnames, updated_docnames, method='update'):
        if build_docnames is None:
            build_docnames = sorted(self.env.all_docs)

        self.info('extracting...')
        for docname in build_docnames:
            # no need to resolve the doctree
            doctree = self.env.get_doctree(docname)
            self.extract(docname, doctree)

    def condition(self, node):
        return (
            isinstance(node, (nodes.literal_block, nodes.comment))
            and node.get('snippet')
        )

    def extract(self, docname, doctree):
        bylang = collections.defaultdict(list)
        for node in doctree.traverse(self.condition):
            bylang[node['language']].append(node)

        for lang, ns in bylang.iteritems():
            filenames = get_lexer_by_name(lang).filenames
            # try to find the first extension glob (*.xyz) in the filename patterns list
            extglob = next(itertools.ifilter(ext_pattern.match, filenames), None)
            if extglob is None:
                print "No extension found for language %s" % lang
            # remove leading * to keep only the actual extension
            ext = extglob[1:]
            outpath = os.path.join(self.outdir, docname + ext)
            with codecs.open(outpath, 'w', encoding='utf-8') as f:
                for node in ns:
                    lines = cStringIO.StringIO(textwrap.dedent(node.astext()))
                    indent = node['indent']
                    # if indent is a number, convert to n-wide space string
                    if indent.isdigit():
                        indent = ' ' * int(indent)
                    if indent:
                        lines = (
                            indent + line
                            for line in lines
                        )

                    f.writelines(lines)
                    f.write('\n\n')


    def get_target_uri(self, docname, typ=None):
        return ''

    def get_outdated_docs(self):
        return self.env.found_docs
