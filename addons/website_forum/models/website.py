from openerp import models, _
from openerp.addons.website.models.website import slug


class website(models.Model):
    _name = 'website'
    _inherit = 'website'

    def search_bar(self, cr, uid, ids, module=None, needle='', context=None):
        data = super(website, self).search_bar(cr, uid,  ids, module=module, needle=needle, context=context)

        if not module or module == 'website_forum':
            _needle = needle not in _('Forum').lower() and needle or ''

            forums = self.pool.get('forum.tag').read_group(cr, uid, ['|', ('name', 'ilike', _needle), ('forum_id', 'ilike', _needle)], ["forum_id"], groupby="forum_id", orderby="forum_id", context=context)

            for forum in forums:
                tag_ids = self.pool.get('forum.tag').search(cr, uid, forum['__domain'], context=context, limit=5)

                children = [{'id': '/tag/%s/questions' % slug(tag), 'text': tag.display_name}
                    for tag in self.pool.get('forum.tag').browse(cr, uid, tag_ids, context=context)]
                data.append({
                    'module': 'website_forum',
                    'url': '/forum/%s' % slug(forum['forum_id']),
                    'text': _('Forum: %s') % forum['forum_id'][1],
                    'children': children,
                })

        return data
