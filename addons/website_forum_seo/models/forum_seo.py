import re
from openerp import models, fields, api

""" Class: ForumSEO

 	Purpose of this forum.seo model store keywords, SEO keywords with optional store URL. 
 	For improving the Forum description more descriptive with seo friendly. 
"""
class ForumSEO(models.Model):
    _name = 'forum.seo'
    _description = 'Forum SEO'
    _rec_name = 'keyword'
    
    keyword = fields.Char(string='Keyword', required="True", help="Keyword", index=True)
    replacement_word = fields.Char(string='New Keyword', help="Replace to a new keyword!")
    url = fields.Text(string='URL', help="Optional URL, The keyword will be replaced by a link to the URL")

    def update_seo_word(self, post_content):
        forum_words = self.search([])
        for keyword, new_word, url in [(forum_word.keyword, forum_word.replacement_word, forum_word.url or None) for forum_word in forum_words]:
            if keyword not in post_content: continue
            seo_word = new_word if new_word else keyword
            pattern = r"%s(?!((?!<).)*<\/a)" % keyword
            replace = "<a href='" + url + "'>" + seo_word + "</a>" if url else new_word
            post_content = re.sub(pattern, replace, post_content, flags=re.U|re.M)
        return post_content
