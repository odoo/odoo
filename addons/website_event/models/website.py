from openerp import models, _, tools
from datetime import datetime


class website(models.Model):
    _name = 'website'
    _inherit = 'website'

    def search_bar(self, cr, uid, ids, module=None, needle='', context=None):
        data = super(website, self).search_bar(cr, uid,  ids, module=module, needle=needle, context=context)

        if not module or module == 'website_event':
            event_obj = self.pool.get('event.event')
            _needle = needle not in _('Events').lower() and needle or ''

            children_date = [child for child in [
                    {'id': '?date=today', 'text': _('Today')},
                    {'id': '?date=week', 'text': _('This Week')},
                    {'id': '?date=nextweek', 'text': _('Next Week')},
                    {'id': '?date=month', 'text': _('This month')},
                    {'id': '?date=nextmonth', 'text': _('Next month')},
                ] if _needle in child['text'].lower()]
            data.append({
                'module': 'website_event',
                'url': '/event',
                'text': _('Events Date'),
                'children': children_date,
            })

            types = event_obj.read_group(cr, uid, [('type', 'ilike', _needle)], ["id", "type"], groupby="type", orderby="type", context=context)
            data.append({
                'module': 'website_event',
                'url': '/event',
                'text': _('Events Type'),
                'children': [{'id': '?type=%s' % _type['type'][0], 'text': _type['type'][1]} for _type in types],
            })

            countries = event_obj.read_group(cr, uid, [('country_id', 'ilike', _needle)], ["id", "country_id"], groupby="country_id", orderby="country_id", context=context)
            data.append({
                'module': 'website_event',
                'url': '/event',
                'text': _('Events Country'),
                'children': [{'id': '?country_id=%s' % country['country_id'][0], 'text': country['country_id'][1]} for country in countries],
            })

        return data
