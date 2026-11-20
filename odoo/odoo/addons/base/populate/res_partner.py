
import collections
import logging

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = "res.partner"
    _populate_dependencies = ["res.company", "res.partner.industry"]

    _populate_sizes = {
        'small': 100,
        'medium': 2000,
        'large': 100000,
    }

    def _populate_factories(self):

        # example of more complex generator composed of multiple sub generators
        # this define one subgenerator per "country"
        address_factories_groups = [
            [ # Falsy, 2 records
                ('street', populate.iterate([False, ''])),
                ('street2', populate.iterate([False, ''])),
                ('city', populate.iterate([False, ''])),
                ('zip', populate.iterate([False, ''])),
                ('country_id', populate.iterate([False])),
            ], [  # BE, 1 record
                ('street', populate.iterate(['Boulevard Tintin {counter}'])),
                ('city', populate.iterate(['Brussels'])),
                ('zip', populate.iterate([1020])),
                ('country_id', populate.iterate([self.env.ref('base.be').id])),
            ], [  # US, 3 records
                ('street', populate.iterate(['Main street', '3th street {counter}', False])),
                ('street2', populate.iterate([False, '', 'Behind the tree {counter}'], [90, 5, 5])),
                ('city', populate.randomize(['Sans Fransisco', 'Los Angeles', '', False])),
                ('zip', populate.iterate([False, '', '50231'])),
                ('country_id', populate.iterate([self.env.ref('base.us').id])),
            ], [  # IN, 2 records
                ('street', populate.iterate(['Main Street', 'Some Street {counter}'])),
                ('city', populate.iterate(['ગાંધીનગર (Gandhinagar)'])),
                ('zip', populate.randomize(['382002', '382008'])),
                ('country_id', populate.randomize([self.env.ref('base.in').id])),
            ], [  # other corner cases, 4 records
                ('street', populate.iterate(['万泉寺村', 'საბჭოს სკვერი {counter}', '10th Street {counter}'])),
                ('city', populate.iterate(['北京市', 'თბილისი', 'دبي'])),
                ('zip', populate.iterate([False, 'UF47', '0', '10201'])),
                ('country_id', populate.randomize([False] + self.env['res.country'].search([]).ids)),
            ]
        ]

        def generate_address(iterator, *args):
            address_generators = [populate.chain_factories(address_factories, self._name) for address_factories in address_factories_groups]
            # first, exhaust all address_generators
            for adress_generator in address_generators:
                for adress_values in adress_generator:
                    if adress_values['__complete']:
                        break
                    values = next(iterator)  # only consume main iterator if usefull
                    yield {**values, **adress_values}

            # then, go pseudorandom between generators
            r = populate.Random('res.partner+address_generator_selector')
            for values in iterator:
                adress_generator = r.choice(address_generators)
                adress_values = next(adress_generator)
                yield {**adress_values, **values}

        # state based on country
        states = self.env['res.country.state'].search([])
        states_per_country = collections.defaultdict(list)
        for state in states:
            states_per_country[state.country_id.id].append(state.id)

        def get_state(values=None, random=None, **kwargs):
            country_id = values['country_id']
            if not country_id:
                return False
            return random.choice([False] + states_per_country[country_id])

        def get_name(values=None, counter=0, **kwargs):
            is_company = values['is_company']
            complete = values['__complete']
            return  '%s_%s_%s' % ('company' if is_company else 'partner', int(complete), counter)

        industry_ids = self.env.registry.populated_models['res.partner.industry']
        company_ids = self.env.registry.populated_models['res.company']

        # not defined fields: vat, partner_longitude, date, partner_latitude, color, company_name, employee, lang, user_id
        return [
            ('active', populate.cartesian([True, False], [0.9, 0.1])),
            ('employee', populate.cartesian([True, False], [0.1, 0.9])),
            ('email', populate.iterate(
                [False, '', 'email{counter}@example.com', '<contact 万> contact{counter}@anotherexample.com', 'invalid_email'])),
            ('type', populate.constant('contact')),  # todo add more logic, manage 'invoice', 'delivery', 'other'
            ('is_company', populate.iterate([True, False], [0.05, 0.95])),
            ('_address', generate_address),
            ('state_id', populate.compute(get_state)),
            ('phone', populate.randomize([False, '', '+3212345678', '003212345678', '12345678'])),
            ('mobile', populate.randomize([False, '', '+32412345678', '0032412345678', '412345678'])),
            ('title', populate.randomize(self.env['res.partner.title'].search([]).ids)),
            ('function', populate.randomize(
                [False, '', 'President of Sales', 'Senior Consultant', 'Product owner', 'Functional Consultant', 'Chief Executive Officer'],
                [50, 10, 2, 20, 5, 10, 1])),
            ('tz', populate.randomize([tz for tz in self.env['res.partner']._fields['tz'].get_values(self.env)])),
            ('website', populate.randomize([False, '', 'http://www.example.com'])),
            ('name', populate.compute(get_name)),  # keep after is_company
            ('ref', populate.randomize([False, '', '{counter}', 'p-{counter}'], [10, 10, 30, 50])),
            ('industry_id', populate.randomize(
                [False] + industry_ids,
                [0.5] + ([0.5/(len(industry_ids) or 1)] * len(industry_ids)))),
            ('comment', populate.iterate([False, '', 'This is a partner {counter}'])),
            ('company_id', populate.iterate(
                [False, self.env.ref('base.main_company').id] + company_ids,
                [1, 1] + [1/(len(company_ids) or 1)]*len(company_ids))),
            ('parent_id', populate.constant(False)),  # will be setted in _populate override
        ]

    def _populate(self, size):
        records = super()._populate(size)
        # set parent_ids
        self._populate_set_companies(records)
        return records

    def _populate_set_companies(self, records):
        _logger.info('Setting companies')
        r_company = populate.Random('res.partner+company_has_partners')
        r_partner = populate.Random('res.partner+partner_has_company')
        r_company_pick = populate.Random('res.partner+partner_company_pick=')

        companies = records.filtered(lambda p: p.is_company and r_company.getrandbits(1))  # 50% change to have partners
        partners = records.filtered(lambda p: not p.is_company and r_partner.getrandbits(1))  # 50% change to have a company

        companies_partners = collections.defaultdict(lambda: self.env['res.partner'])
        for partner in partners:
            companies_partners[r_company_pick.choice(companies)] |= partner

        # batching company write improves performances a lot (~40% faster for total partner creation).
        for count, (company, partners) in enumerate(companies_partners.items(), start=1):
            if count % 100 == 0:
                _logger.info('Setting company: %s/%s', count, len(companies))
            partners.write({'parent_id': company.id})
            partners._onchange_company_id()

class ResPartnerIndustry(models.Model):
    _inherit = "res.partner.industry"

    _populate_sizes = {
        'small': 15,
        'medium': 60,
        'large': 300,
    }

    def _populate_factories(self):
        return [
            ('active', populate.cartesian([False, True], [0.1, 0.9])),
            ('name', populate.cartesian(
                [False, 'Industry name', 'Industry name {counter}'],
                [0.08, 0.01, 0.9])),
            ('full_name', populate.iterate([False, 'Industry full name %s']))
        ]
