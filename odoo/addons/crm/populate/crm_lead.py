# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import models
from odoo.tools import populate
from odoo.addons.crm.populate import tools


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    _populate_dependencies = [
        'res.partner',  # customer
    ]
    _populate_sizes = {
        'small': 5,
        'medium': 150,
        'large': 400
    }

    def _populate_factories(self):
        partner_ids = self.env.registry.populated_models['res.partner']

        # phone based on country
        country_be, country_us, country_in = self.env.ref('base.be'), self.env.ref('base.us'), self.env.ref('base.in')
        phones_per_country = {
            country_be.id: [False, '+32456555432', '+32456555675', '+32456555627'],
            country_us.id: [False, '+15555564246', '+15558455343', '+15557129033'],
            country_in.id: [False, '+919755538077', '+917555765232', '+918555199309'],
            False: [False, '', '+3212345678', '003212345678', '12345678'],
        }

        # example of more complex generator composed of multiple sub generators
        # this define one subgenerator per "country"
        address_factories_groups = [
            [ # Falsy, 2 records
                ('street', populate.iterate([False, ''])),
                ('street2', populate.iterate([False, ''])),
                ('city', populate.iterate([False, ''])),
                ('zip', populate.iterate([False, ''])),
                ('country_id', populate.iterate([False])),
            ], [  # BE, 2 records
                ('street', populate.iterate(['Rue des Bourlottes {counter}', 'Rue Pinckaers {counter}'])),
                ('city', populate.iterate(['Brussels', 'Ramillies'])),
                ('zip', populate.iterate([1020, 1367])),
                ('country_id', populate.iterate([self.env.ref('base.be').id])),
            ], [  # US, 3 records
                ('street', populate.iterate(['Main street', '3th street {counter}', False])),
                ('street2', populate.iterate([False, '', 'Behind the tree {counter}'], [90, 5, 5])),
                ('city', populate.randomize(['San Fransisco', 'Los Angeles', '', False])),
                ('zip', populate.iterate([False, '', '50231'])),
                ('country_id', populate.iterate([self.env.ref('base.us').id])),
            ], [  # IN, 2 records
                ('street', populate.iterate(['Main Street', 'Some Street {counter}'])),
                ('city', populate.iterate(['ગાંધીનગર (Gandhinagar)'])),
                ('zip', populate.randomize(['382002', '382008'])),
                ('country_id', populate.randomize([self.env.ref('base.in').id])),
            ], [  # other corner cases, 2 records
                ('street', populate.iterate(['万泉寺村', 'საბჭოს სკვერი {counter}'])),
                ('city', populate.iterate(['北京市', 'თბილისი'])),
                ('zip', populate.iterate([False, 'UF47'])),
                ('country_id', populate.randomize([False] + self.env['res.country'].search([]).ids)),
            ]
        ]

        address_generators = [
            populate.chain_factories(address_factories, self._name)
            for address_factories in address_factories_groups
        ]

        def _compute_address(iterator, *args):
            r = populate.Random('res.partner+address_generator_selector')

            for values in iterator:
                if values['partner_id']:
                    yield {**values}
                else:
                    address_gen = r.choice(address_generators)
                    address_values = next(address_gen)
                    yield {**values, **address_values}

        def _compute_contact(iterator, *args):
            r = populate.Random('res.partner+contact_generator_selector')

            for values in iterator:
                if values['partner_id']:
                    yield {**values}
                else:
                    fn = r.choice(tools._p_forename_groups)
                    mn = r.choices(
                        [False] + tools._p_middlename_groups,
                        weights=[1] + [1 / (len(tools._p_middlename_groups) or 1)] * len(tools._p_middlename_groups)
                    )[0]
                    sn = r.choice(tools._p_surname_groups)
                    mn_wseparator = f' "{mn}" '
                    contact_name = f'{fn}{mn_wseparator}{sn}'

                    country_id = values['country_id']
                    if country_id not in phones_per_country.keys():
                        country_id = False
                    mobile = r.choice(phones_per_country[country_id])
                    phone = r.choice(phones_per_country[country_id])

                    yield {**values,
                           'contact_name': contact_name,
                           'mobile': mobile,
                           'phone': phone,
                          }

        def _compute_contact_name(values=None, counter=0, **kwargs):
            """ Generate lead names a bit better than lead_counter because this is Odoo. """
            partner_id = values['partner_id']
            complete = values['__complete']

            fn = kwargs['random'].choice(tools._p_forename_groups)
            mn = kwargs['random'].choices(
                [False] + tools._p_middlename_groups,
                weights=[1] + [1 / (len(tools._p_middlename_groups) or 1)] * len(tools._p_middlename_groups)
            )[0]
            sn = kwargs['random'].choice(tools._p_surname_groups)
            return  '%s%s %s (%s_%s (partner %s))' % (
                fn,
                ' "%s"' % mn if mn else '',
                sn,
                int(complete),
                counter,
                partner_id
            )

        def _compute_date_open(random=None, values=None, **kwargs):
            user_id = values['user_id']
            if user_id:
                delta = random.randint(0, 10)
                return datetime.now() - timedelta(days=delta)
            return False

        def _compute_name(values=None, counter=0, **kwargs):
            """ Generate lead names a bit better than lead_counter because this is Odoo. """
            complete = values['__complete']

            fn = kwargs['random'].choice(tools._case_prefix_groups)
            sn = kwargs['random'].choice(tools._case_object_groups)
            return  '%s %s (%s_%s)' % (
                fn,
                sn,
                int(complete),
                counter
            )

        return [
            ('partner_id', populate.iterate(
                [False] + partner_ids,
                [2] + [1 / (len(partner_ids) or 1)] * len(partner_ids))
            ),
            ('_address', _compute_address),  # uses partner_id
            ('_contact', _compute_contact),  # uses partner_id, country_id
            ('user_id', populate.iterate(
                [False],
                )
            ),
            ('date_open', populate.compute(_compute_date_open)),  # uses user_id
            ('name', populate.compute(_compute_name)),
            ('type', populate.iterate(['lead', 'opportunity'], [0.8, 0.2])),
        ]
