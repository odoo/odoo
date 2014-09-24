# -*- coding: utf-8 -*-

import re
from urlparse import urlparse
from openerp import models, fields, api


class ForumSEO(models.Model):
    """ ForumSeo models keywords and their respective replacement word, along with optional URL.
        Keywords will be replaced in every forum post by the replacement word.
        If the URL is defined, the replacement word will be a link tag leading to the stored URL.
        Note that keywords detection set either case sensitive or insensitive, default insensitive.
    """
    _name = 'forum.seo'
    _description = 'Forum SEO'
    _rec_name = 'keyword'

    keyword = fields.Char('Keyword', required="True", help="Keyword", index=True)
    replacement_word = fields.Char('New Keyword', help="Replace to a new keyword!")
    url = fields.Char('URL', help="Optional URL, The keyword will be replaced by a link to the URL.")
    case_sensitive = fields.Boolean('Case Sensitive', help="Optional case sensitive, Case sensitive matching exactly same word.")

    def _url_valid(self, url):
        parsed = urlparse(url)
        if not (parsed.scheme) and not ('//' in url):
            url = '%s%s' % ('http://', url)
        return url

    @api.model
    def create(self, values):
        if values.get('url'):
            values.update({'url': self._url_valid(values['url'])})
        return super(ForumSEO, self).create(values)

    @api.multi
    def write(self, values):
        if values.get('url'):
            values.update({'url': self._url_valid(values['url'])})
        return super(ForumSEO, self).write(values)

    def update_seo_word(self, post_content):
        forum_words = self.search([]).sorted(key=lambda t: len(t.keyword), reverse=True)
        seo_words = [(forum_word.keyword, forum_word.replacement_word, forum_word.url or None, forum_word.case_sensitive) for forum_word in forum_words]

        """ RegExp Pattern used for replace seo friendly keyword along with optional URL.
        Example:
            Pattern:
                (?<!(?=((http|https|ftp|ftps?)\:\/\/?)(www\.?)))odoo(?!(?:([$&+.,/:;\-_#=@?!a-zA-Z0-9](?!\s))+))(?=[^<>]*<)(?!(?:(?!</?(?:a|span)[ >/])(?:.|\n))*</(?:a|span)>)(?! (odoo))
            Post Content:
                "<p>Odoo url become now www.odoo.com. 'odoo' is OpenSource ERP System.</p>
                <p>Odoo CRM is application of Odoo.</p>
                <p>Odoo CMS is newest released for website builder.</p>"
            After Content:
                "<p><a href="http://www.odoo.com"><span>Odoo</span></a> url become now www.odoo.com. '<a href="http://www.odoo.com"><span>Odoo</span></a>' is OpenSource ERP System.</p>
                <p><a href="https://www.odoo.com/page/crm"><span>Odoo CRM</span></a> is application of <a href="http://www.odoo.com"><span>Odoo</span></a>.</p>
                <p><a href="https://www.odoo.com/page/website-builder"><span>Odoo Wesite Builder</span></a> is newest released for website builder.</p>"
        """
        protocols_name = ['http', 'https', 'ftp', 'ftps']
        protocols = '|'.join(protocols_name)

        prefix = "(?<!(?=((%s?)\:\/\/?)(www\.?)))" % (protocols)
        postfix = "(?!(?:([$&+.,/:;\-_#=@?!a-zA-Z0-9](?!\s|<))+))"

        tag_name = ['a', 'span']
        tags = '|'.join(tag_name)
        tag_filter = "(?=[^<>]*<)(?!(?:(?!</?(?:%s)[ >/])(?:.|\\n))*</(?:%s)>)" % (tags, tags)

        for seo_word in seo_words:
            keyword, replacement_word, url, case_sensitive = seo_word[0], seo_word[1], seo_word[2], seo_word[3]
            if keyword.lower() not in post_content.lower() or not (replacement_word or url):
                continue
            new_word = replacement_word if replacement_word else keyword

            seo_word_list = [w if re.compile(r"[\w]+|[.,!?;]").split(w) else w for w in new_word.split()]
            seo_word_OR = '|'.join(seo_word_list)
            endfix = "(?! (%s))" % (seo_word_OR)  # Ignore if keyword after the word is part of new keyword contain

            replace = "<a href='%s'><span>%s</span></a>" % (url, new_word) if url else "<span>%s</span>" % (replacement_word)
            pattern = r"%s%s%s%s%s" % (prefix, keyword, postfix, tag_filter, endfix)
            flag = re.M if case_sensitive else re.I|re.M
            post_content = re.sub(pattern, replace, post_content, flags=flag)

        return post_content

class Post(models.Model):
    _inherit = 'forum.post'

    @api.model
    def create(self, vals):
        if vals.get('content'):
            vals['content'] = self.env['forum.seo'].update_seo_word(vals['content'])
        return super(Post, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('content'):
            vals['content'] = self.env['forum.seo'].update_seo_word(vals['content'])
        return super(Post, self).write(vals)
