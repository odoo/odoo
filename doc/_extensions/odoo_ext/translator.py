# -*- coding: utf-8 -*-
from __future__ import print_function

import os.path
import posixpath
import re
try:
    from urllib.request import url2pathname  # pylint: disable=deprecated-module
except ImportError:
    from urllib import url2pathname  # pylint: disable=deprecated-module

from docutils import nodes
from sphinx import addnodes, util
from sphinx.locale import admonitionlabels

from odoo.tools import pycompat


def _parents(node):
    while node.parent:
        node = node.parent
        yield node

class BootstrapTranslator(nodes.NodeVisitor, object):
    head_prefix = 'head_prefix'
    head = 'head'
    stylesheet = 'stylesheet'
    body_prefix = 'body_prefix'
    body_pre_docinfo = 'body_pre_docinfo'
    docinfo = 'docinfo'
    body_suffix = 'body_suffix'
    subtitle = 'subtitle'
    header = 'header'
    footer = 'footer'
    html_prolog = 'html_prolog'
    html_head = 'html_head'
    html_title = 'html_title'
    html_subtitle = 'html_subtitle'

    # <meta> tags
    meta = [
        '<meta http-equiv="X-UA-Compatible" content="IE=edge">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
    ]

    def __init__(self, builder, document):
        super(BootstrapTranslator, self).__init__(document)
        self.builder = builder
        self.body = []
        self.fragment = self.body
        self.html_body = self.body
        # document title
        self.title = []
        self.start_document_title = 0
        self.first_title = False

        self.context = []
        self.section_level = 0

        self.highlightlang = self.highlightlang_base = self.builder.config.highlight_language
        self.highlightopts = getattr(builder.config, 'highlight_options', {})

        self.first_param = 1
        self.optional_param_level = 0
        self.required_params_left = 0
        self.param_separator = ','

    def encode(self, text):
        return pycompat.text_type(text).translate({
            ord('&'): u'&amp;',
            ord('<'): u'&lt;',
            ord('"'): u'&quot;',
            ord('>'): u'&gt;',
            0xa0: u'&nbsp;'
        })

    def starttag(self, node, tagname, **attributes):
        tagname = pycompat.text_type(tagname).lower()

        # extract generic attributes
        attrs = {name.lower(): value for name, value in attributes.items()}
        attrs.update(
            (name, value) for name, value in node.attributes.items()
            if name.startswith('data-')
        )

        prefix = []
        postfix = []

        # handle possibly multiple ids
        assert 'id' not in attrs, "starttag can't be passed a single id attribute, use a list of ids"
        ids = node.get('ids', []) + attrs.pop('ids', [])
        if ids:
            _ids = iter(ids)
            attrs['id'] = next(_ids)
            postfix.extend(u'<i id="{}"></i>'.format(_id) for _id in _ids)

        # set CSS class
        classes = set(node.get('classes', []) + attrs.pop('class', '').split())
        if classes:
            attrs['class'] = u' '.join(classes)

        return u'{prefix}<{tag} {attrs}>{postfix}'.format(
            prefix=u''.join(prefix),
            tag=tagname,
            attrs=u' '.join(u'{}="{}"'.format(name, self.attval(value))
                            for name,  value in attrs.items()),
            postfix=u''.join(postfix),
        )
    # only "space characters" SPACE, CHARACTER TABULATION, LINE FEED,
    # FORM FEED and CARRIAGE RETURN should be collapsed, not al White_Space
    def attval(self, value, whitespace=re.compile(u'[ \t\n\f\r]+')):
        return self.encode(whitespace.sub(u' ', pycompat.text_type(value)))

    def astext(self):
        return u''.join(self.body)

    def unknown_visit(self, node):
        print("unknown node", node.__class__.__name__)
        self.body.append(u'[UNKNOWN NODE {}]'.format(node.__class__.__name__))
        raise nodes.SkipNode

    def visit_highlightlang(self, node):
        self.highlightlang = node['lang']
    def depart_highlightlang(self, node):
        pass

    def visit_document(self, node):
        self.first_title = True
    def depart_document(self, node):
        pass

    def visit_section(self, node):
        # close "parent" or preceding section, unless this is the opening of
        # the first section
        if self.section_level:
            self.body.append(u'</section>')
        self.section_level += 1

        self.body.append(self.starttag(node, 'section'))
    def depart_section(self, node):
        self.section_level -= 1
        # close last section of document
        if not self.section_level:
            self.body.append(u'</section>')

    def visit_topic(self, node):
        self.body.append(self.starttag(node, 'nav'))
    def depart_topic(self, node):
        self.body.append(u'</nav>')

    def is_compact_paragraph(self, node):
        parent = node.parent
        if isinstance(parent, (nodes.document, nodes.compound,
                               addnodes.desc_content,
                               addnodes.versionmodified)):
            # Never compact paragraphs in document or compound.
            return False

        for key, value in node.attlist():
            # we can ignore a few specific classes, all other non-default
            # attributes require that a <p> node remains
            if key != 'classes' or value not in ([], ['first'], ['last'], ['first', 'last']):
                return False

        first = isinstance(node.parent[0], nodes.label)
        for child in parent.children[first:]:
            # only first paragraph can be compact
            if isinstance(child, nodes.Invisible):
                continue
            if child is node:
                break
            return False
        parent_length = len([
            1 for n in parent
            if not isinstance(n, (nodes.Invisible, nodes.label))
        ])
        return parent_length == 1

    def visit_paragraph(self, node):
        if self.is_compact_paragraph(node):
            self.context.append(u'')
            return
        self.body.append(self.starttag(node, 'p'))
        self.context.append(u'</p>')
    def depart_paragraph(self, node):
        self.body.append(self.context.pop())
    def visit_compact_paragraph(self, node):
        pass
    def depart_compact_paragraph(self, node):
        pass

    def visit_literal_block(self, node):
        if node.rawsource != node.astext():
            # most probably a parsed-literal block -- don't highlight
            self.body.append(self.starttag(node, 'pre'))
            return
        lang = self.highlightlang
        highlight_args = node.get('highlight_args', {})
        if 'language' in node:
            # code-block directives
            lang = node['language']
            highlight_args['force'] = True
        linenos = node.get('linenos', False)
        if lang is self.highlightlang_base:
            # only pass highlighter options for original language
            opts = self.highlightopts
        else:
            opts = {}

        def warner(msg, **kw):
            self.builder.warn(msg, (self.builder.current_docname, node.line))
        highlighted = self.builder.highlighter.highlight_block(
            node.rawsource, lang, opts=opts, warn=warner, linenos=linenos,
            **highlight_args)
        self.body.append(self.starttag(node, 'div', CLASS='highlight-%s' % lang))
        self.body.append(highlighted)
        self.body.append(u'</div>\n')
        raise nodes.SkipNode
    def depart_literal_block(self, node):
        self.body.append(u'</pre>')

    def visit_bullet_list(self, node):
        self.body.append(self.starttag(node, 'ul'))
    def depart_bullet_list(self, node):
        self.body.append(u'</ul>')
    def visit_enumerated_list(self, node):
        self.body.append(self.starttag(node, 'ol'))
    def depart_enumerated_list(self, node):
        self.body.append(u'</ol>')
    def visit_list_item(self, node):
        self.body.append(self.starttag(node, 'li'))
    def depart_list_item(self, node):
        self.body.append(u'</li>')
    def visit_definition_list(self, node):
        self.body.append(self.starttag(node, 'dl'))
    def depart_definition_list(self, node):
        self.body.append(u'</dl>')
    def visit_definition_list_item(self, node):
        pass
    def depart_definition_list_item(self, node):
        pass
    def visit_term(self, node):
        self.body.append(self.starttag(node, 'dt'))
    def depart_term(self, node):
        self.body.append(u'</dt>')
    def visit_termsep(self, node):
        self.body.append(self.starttag(node, 'br'))
        raise nodes.SkipNode
    def visit_definition(self, node):
        self.body.append(self.starttag(node, 'dd'))
    def depart_definition(self, node):
        self.body.append(u'</dd>')

    def visit_admonition(self, node, type=None):
        clss = {
            # ???: 'alert-success',

            'note': 'alert-info',
            'hint': 'alert-info',
            'tip': 'alert-info',
            'seealso': 'alert-go_to',

            'warning': 'alert-warning',
            'attention': 'alert-warning',
            'caution': 'alert-warning',
            'important': 'alert-warning',

            'danger': 'alert-danger',
            'error': 'alert-danger',

            'exercise': 'alert-exercise',
        }
        self.body.append(self.starttag(node, 'div', role='alert', CLASS='alert {}'.format(
            clss.get(type, '')
        )))
        if 'alert-dismissible' in node.get('classes', []):
            self.body.append(
                u'<button type="button" class="close" data-dismiss="alert" aria-label="Close">'
                u'<span aria-hidden="true">&times;</span>'
                u'</button>')
        if type:
            node.insert(0, nodes.title(type, admonitionlabels[type]))
    def depart_admonition(self, node):
        self.body.append(u'</div>')
    visit_note = lambda self, node: self.visit_admonition(node, 'note')
    visit_warning = lambda self, node: self.visit_admonition(node, 'warning')
    visit_attention = lambda self, node: self.visit_admonition(node, 'attention')
    visit_caution = lambda self, node: self.visit_admonition(node, 'caution')
    visit_danger = lambda self, node: self.visit_admonition(node, 'danger')
    visit_error = lambda self, node: self.visit_admonition(node, 'error')
    visit_hint = lambda self, node: self.visit_admonition(node, 'hint')
    visit_important = lambda self, node: self.visit_admonition(node, 'important')
    visit_tip = lambda self, node: self.visit_admonition(node, 'tip')
    visit_exercise = lambda self, node: self.visit_admonition(node, 'exercise')
    visit_seealso = lambda self, node: self.visit_admonition(node, 'seealso')
    depart_note = depart_admonition
    depart_warning = depart_admonition
    depart_attention = depart_admonition
    depart_caution = depart_admonition
    depart_danger = depart_admonition
    depart_error = depart_admonition
    depart_hint = depart_admonition
    depart_important = depart_admonition
    depart_tip = depart_admonition
    depart_exercise = depart_admonition
    depart_seealso = depart_admonition
    def visit_versionmodified(self, node):
        self.body.append(self.starttag(node, 'div', CLASS=node['type']))
    def depart_versionmodified(self, node):
        self.body.append(u'</div>')

    def visit_title(self, node):
        parent = node.parent
        closing = u'</h3>'
        if isinstance(parent, nodes.Admonition):
            self.body.append(self.starttag(node, 'h3', CLASS='alert-title'))
        elif isinstance(node.parent, nodes.document):
            self.body.append(self.starttag(node, 'h1'))
            closing = u'</h1>'
            self.start_document_title = len(self.body)
        else:
            assert isinstance(parent, nodes.section), "expected a section node as parent to the title, found {}".format(parent)
            if self.first_title:
                self.first_title = False
                raise nodes.SkipNode()
            nodename = 'h{}'.format(self.section_level)
            self.body.append(self.starttag(node, nodename))
            closing = u'</{}>'.format(nodename)
        self.context.append(closing)
    def depart_title(self, node):
        self.body.append(self.context.pop())
        if self.start_document_title:
            self.title = self.body[self.start_document_title:-1]
            self.start_document_title = 0
            del self.body[:]

    # the rubric should be a smaller heading than the current section, up to
    # h6... maybe "h7" should be a ``p`` instead?
    def visit_rubric(self, node):
        self.body.append(self.starttag(node, 'h{}'.format(min(self.section_level + 1, 6))))
    def depart_rubric(self, node):
        self.body.append(u'</h{}>'.format(min(self.section_level + 1, 6)))

    def visit_block_quote(self, node):
        self.body.append(self.starttag(node, 'blockquote'))
    def depart_block_quote(self, node):
        self.body.append(u'</blockquote>')
    def visit_attribution(self, node):
        self.body.append(self.starttag(node, 'footer'))
    def depart_attribution(self, node):
        self.body.append(u'</footer>')

    def visit_container(self, node):
        self.body.append(self.starttag(node, 'div'))
    def depart_container(self, node):
        self.body.append(u'</div>')
    def visit_compound(self, node):
        self.body.append(self.starttag(node, 'div'))
    def depart_compound(self, node):
        self.body.append(u'</div>')

    def visit_image(self, node):
        uri = node['uri']
        if uri in self.builder.images:
            uri = posixpath.join(self.builder.imgpath,
                                 self.builder.images[uri])
        attrs = {'src': uri, 'class': 'img-responsive'}
        if 'alt' in node:
            attrs['alt'] = node['alt']
        if 'align' in node:
            if node['align'] == 'center':
                attrs['class'] += ' center-block'
            else:
                doc = None
                if node.source:
                    doc = node.source
                    if node.line:
                        doc += ':%d' % node.line
                self.builder.app.warn(
                    "Unsupported alignment value \"%s\"" % node['align'],
                    location=doc
                )
        elif 'align' in node.parent and node.parent['align'] == 'center':
            # figure > image
            attrs['class'] += ' center-block'

        # todo: explicit width/height/scale?
        self.body.append(self.starttag(node, 'img', **attrs))
    def depart_image(self, node): pass
    def visit_figure(self, node):
        self.body.append(self.starttag(node, 'div'))
    def depart_figure(self, node):
        self.body.append(u'</div>')
    def visit_caption(self, node):
        # first paragraph of figure content
        self.body.append(self.starttag(node, 'h4'))
    def depart_caption(self, node):
        self.body.append(u'</h4>')
    def visit_legend(self, node): pass
    def depart_legend(self, node): pass

    def visit_line(self, node):
        self.body.append(self.starttag(node, 'div', CLASS='line'))
        # ensure the line still takes the room it needs
        if not len(node): self.body.append(u'<br />')
    def depart_line(self, node):
        self.body.append(u'</div>')

    def visit_line_block(self, node):
        self.body.append(self.starttag(node, 'div', CLASS='line-block'))
    def depart_line_block(self, node):
        self.body.append(u'</div>')

    def visit_table(self, node):
        self.body.append(self.starttag(node, 'table', CLASS='table'))
    def depart_table(self, node):
        self.body.append(u'</table>')
    def visit_tgroup(self, node): pass
    def depart_tgroup(self, node): pass
    def visit_colspec(self, node): raise nodes.SkipNode
    def visit_thead(self, node):
        self.body.append(self.starttag(node, 'thead'))
    def depart_thead(self, node):
        self.body.append(u'</thead>')
    def visit_tbody(self, node):
        self.body.append(self.starttag(node, 'tbody'))
    def depart_tbody(self, node):
        self.body.append(u'</tbody>')
    def visit_row(self, node):
        self.body.append(self.starttag(node, 'tr'))
    def depart_row(self, node):
        self.body.append(u'</tr>')
    def visit_entry(self, node):
        if isinstance(node.parent.parent, nodes.thead):
            tagname = 'th'
        else:
            tagname = 'td'
        self.body.append(self.starttag(node, tagname))
        self.context.append(tagname)
    def depart_entry(self, node):
        self.body.append(u'</{}>'.format(self.context.pop()))

    def visit_Text(self, node):
        self.body.append(self.encode(node.astext()))
    def depart_Text(self, node):
        pass
    def visit_literal(self, node):
        self.body.append(self.starttag(node, 'code'))
    def depart_literal(self, node):
        self.body.append(u'</code>')
    visit_literal_emphasis = visit_literal
    depart_literal_emphasis = depart_literal
    def visit_emphasis(self, node):
        self.body.append(self.starttag(node, 'em'))
    def depart_emphasis(self, node):
        self.body.append(u'</em>')
    def visit_strong(self, node):
        self.body.append(self.starttag(node, 'strong'))
    def depart_strong(self, node):
        self.body.append(u'</strong>')
    visit_literal_strong = visit_strong
    depart_literal_strong = depart_strong
    def visit_inline(self, node):
        self.body.append(self.starttag(node, 'span'))
    def depart_inline(self, node):
        self.body.append(u'</span>')
    def visit_abbreviation(self, node):
        attrs = {}
        if 'explanation' in node:
            attrs['title'] = node['explanation']
        self.body.append(self.starttag(node, 'abbr', **attrs))
    def depart_abbreviation(self, node):
        self.body.append(u'</abbr>')

    def visit_reference(self, node):
        attrs = {
            'class': 'reference',
            'href': node['refuri'] if 'refuri' in node else '#' + node['refid']
        }
        attrs['class'] += ' internal' if (node.get('internal') or 'refuri' not in node) else ' external'
        if any(isinstance(ancestor, nodes.Admonition) for ancestor in _parents(node)):
            attrs['class'] += ' alert-link'

        if 'reftitle' in node:
            attrs['title'] = node['reftitle']

        self.body.append(self.starttag(node, 'a', **attrs))
    def depart_reference(self, node):
        self.body.append(u'</a>')
    def visit_target(self, node): pass
    def depart_target(self, node): pass
    def visit_footnote(self, node):
        self.body.append(self.starttag(node, 'div', CLASS='footnote'))
        self.footnote_backrefs(node)
    def depart_footnote(self, node):
        self.body.append(u'</div>')
    def visit_footnote_reference(self, node):
        self.body.append(self.starttag(
            node, 'a', href='#' + node['refid'], CLASS="footnote-ref"))
    def depart_footnote_reference(self, node):
        self.body.append(u'</a>')
    def visit_label(self, node):
        self.body.append(self.starttag(node, 'span', CLASS='footnote-label'))
        self.body.append(u'%s[' % self.context.pop())
    def depart_label(self, node):
        # Context added in footnote_backrefs.
        self.body.append(u']%s</span> %s' % (self.context.pop(), self.context.pop()))
    def footnote_backrefs(self, node):
        # should store following data on context stack (in that order since
        # they'll be popped so LIFO)
        #
        # * outside (after) label
        # * after label text
        # * before label text
        backrefs = node['backrefs']
        if not backrefs:
            self.context.extend(['', '', ''])
        elif len(backrefs) == 1:
            self.context.extend([
                '',
                '</a>',
                '<a class="footnote-backref" href="#%s">' % backrefs[0]
            ])
        else:
            backlinks = (
                '<a class="footnote-backref" href="#%s">%s</a>' % (backref, i)
                for i, backref in enumerate(backrefs, start=1)
            )
            self.context.extend([
                '<em class="footnote-backrefs">(%s)</em> ' % ', '.join(backlinks),
                '',
                ''
            ])

    def visit_desc(self, node):
        self.body.append(self.starttag(node, 'section', CLASS='code-' + node['objtype']))
    def depart_desc(self, node):
        self.body.append(u'</section>')
    def visit_desc_signature(self, node):
        self.body.append(self.starttag(node, 'h6'))
        self.body.append(u'<code>')
    def depart_desc_signature(self, node):
        self.body.append(u'</code>')
        self.body.append(u'</h6>')
    def visit_desc_addname(self, node): pass
    def depart_desc_addname(self, node): pass
    def visit_desc_type(self, node): pass
    def depart_desc_type(self, node): pass
    def visit_desc_returns(self, node):
        self.body.append(u' → ')
    def depart_desc_returns(self, node):
        pass
    def visit_desc_name(self, node): pass
    def depart_desc_name(self, node): pass
    def visit_desc_parameterlist(self, node):
        self.body.append(u'(')
        self.first_param = True
        self.optional_param_level = 0
        # How many required parameters are left.
        self.required_params_left = sum(isinstance(c, addnodes.desc_parameter) for c in node.children)
        self.param_separator = node.child_text_separator
    def depart_desc_parameterlist(self, node):
        self.body.append(u')')
    # If required parameters are still to come, then put the comma after
    # the parameter.  Otherwise, put the comma before.  This ensures that
    # signatures like the following render correctly (see issue #1001):
    #
    #     foo([a, ]b, c[, d])
    #
    def visit_desc_parameter(self, node):
        if self.first_param:
            self.first_param = 0
        elif not self.required_params_left:
            self.body.append(self.param_separator)
        if self.optional_param_level == 0:
            self.required_params_left -= 1
        if 'noemph' not in node: self.body.append(u'<em>')
    def depart_desc_parameter(self, node):
        if 'noemph' not in node: self.body.append(u'</em>')
        if self.required_params_left:
            self.body.append(self.param_separator)
    def visit_desc_optional(self, node):
        self.optional_param_level += 1
        self.body.append(u'[')
    def depart_desc_optional(self, node):
        self.optional_param_level -= 1
        self.body.append(u']')
    def visit_desc_annotation(self, node):
        self.body.append(self.starttag(node, 'em'))
    def depart_desc_annotation(self, node):
        self.body.append(u'</em>')
    def visit_desc_content(self, node): pass
    def depart_desc_content(self, node): pass
    def visit_field_list(self, node):
         self.body.append(self.starttag(node, 'div', CLASS='code-fields'))
    def depart_field_list(self, node):
        self.body.append(u'</div>')
    def visit_field(self, node):
        self.body.append(self.starttag(node, 'div', CLASS='code-field'))
    def depart_field(self, node):
        self.body.append(u'</div>')
    def visit_field_name(self, node):
        self.body.append(self.starttag(node, 'div', CLASS='code-field-name'))
    def depart_field_name(self, node):
        self.body.append(u'</div>')
    def visit_field_body(self, node):
        self.body.append(self.starttag(node, 'div', CLASS='code-field-body'))
    def depart_field_body(self, node):
        self.body.append(u'</div>')

    def visit_glossary(self, node): pass
    def depart_glossary(self, node): pass

    def visit_comment(self, node): raise nodes.SkipNode
    def visit_toctree(self, node):
        # div class=row {{ section_type }}
        #   h2 class=col-sm-12
        #     {{ section title }}
        #   div class=col-sm-6 col-md-3
        #     figure class=card
        #       a href=current_link style=background-image: document-image-attribute class=card-img
        #         figcaption
        #           {{ card title }}
        env = self.builder.env
        conf = self.builder.app.config
        for title, ref in ((e[0], e[1]) for e in node['entries']):
            # external URL, no toc, can't recurse into
            if ref not in env.tocs:
                continue
            toc = env.tocs[ref].traverse(addnodes.toctree)

            classes = env.metadata[ref].get('types', 'tutorials')
            classes += ' toc-single-entry' if not toc else ' toc-section'
            self.body.append(self.starttag(node, 'div', CLASS="row " + classes))
            self.body.append(u'<div class="col-sm-12"><h2>')
            self.body.append(title if title else util.nodes.clean_astext(env.titles[ref]))
            self.body.append(u'</h2></div>')

            entries = [(title, ref)] if not toc else ((e[0], e[1]) for e in toc[0]['entries'])
            for subtitle, subref in entries:
                baseuri = self.builder.get_target_uri(node['parent'])

                if subref in env.metadata:
                    cover = env.metadata[subref].get('banner', conf.odoo_cover_default)
                elif subref in conf.odoo_cover_external:
                    cover = conf.odoo_cover_external[subref]
                else:
                    cover = conf.odoo_cover_default_external

                if cover:
                    banner = '_static/' + cover
                    base, ext = os.path.splitext(banner)
                    small = "{}.small{}".format(base, ext)
                    if os.path.isfile(url2pathname(small)):
                        banner = small
                    style = u"background-image: url('{}')".format(
                        util.relative_uri(baseuri, banner) or '#')
                else:
                    style = u''

                self.body.append(u"""
                <div class="col-sm-6 col-md-3">
                <figure class="card">
                    <a href="{link}" class="card-img">
                        <span style="{style}"></span>
                        <figcaption>{title}</figcaption>
                    </a>
                </figure>
                </div>
                """.format(
                    link=subref if util.url_re.match(subref) else util.relative_uri(
                        baseuri, self.builder.get_target_uri(subref)),
                    style=style,
                    title=subtitle if subtitle else util.nodes.clean_astext(env.titles[subref]),
                ))

            self.body.append(u'</div>')
        raise nodes.SkipNode

    def visit_index(self, node): raise nodes.SkipNode

    def visit_raw(self, node):
        if 'html' in node.get('format', '').split():
            t = 'span' if isinstance(node.parent, nodes.TextElement) else 'div'
            if node['classes']:
                self.body.append(self.starttag(node, t))
            self.body.append(node.astext())
            if node['classes']:
                self.body.append('</%s>' % t)
        # Keep non-HTML raw text out of output:
        raise nodes.SkipNode

    # internal node
    def visit_substitution_definition(self, node): raise nodes.SkipNode

    # without set_translator, add_node doesn't work correctly, so the
    # serialization of html_domain nodes needs to be embedded here
    def visit_div(self, node):
        self.body.append(self.starttag(node, 'div'))
    def depart_div(self, node):
        self.body.append(u'</div>\n')
    def visit_address(self, node):
        self.body.append(self.starttag(node, 'address'))
    def depart_address(self, node):
        self.body.append(u'</address>')
    # TODO: inline elements
