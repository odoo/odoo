from odoo.tests import common
from collections import OrderedDict
from odoo.exceptions import AccessError


class TestRelated(common.TransactionCase):
    ''' Test grouping by related non-stored fields. '''

    def test_related(self):
        Partner = self.env['res.partner']
        Model1 = self.env['test_read_group.related1']
        Model2 = self.env['test_read_group.related2']
        Model3 = self.env['test_read_group.related3']
        Model3NoSudo = self.env['test_read_group.related3.nosudo']
        Model3AllDelegate = (Model3, Model3NoSudo)
        Model3NoSudoNoDelegate = self.env['test_read_group.related3.nosudo.nodelegate']

        country = self.env.ref('base.ru')
        state1 = self.env['res.country.state'].create({
            'name': 'Bashkortostan',
            'code': 'RU-BA',
            'country_id': country.id,
        })
        state2 = self.env['res.country.state'].create({
            'name': 'Tatarstan',
            'code': 'RU-TA',
            'country_id': country.id,
        })

        for model in Model3AllDelegate:
            for state in (state1, state2, None):
                for name in ('Ivanov', 'Petrov'):
                    model.create({
                        'partner_id': Partner.create({
                            'name': 'Ivan %s %s' % (name, state and 'from ' + state.name or 'who forgot his origins'),
                            'country_id': country.id,
                            'state_id': state and state.id,
                        }).id
                    })

        self.env.flush_all()

        # sudo mode
        for model in Model3AllDelegate:
            self.make_test(model, 'state_code')
            self.make_test(model, 'state_code2')
            self.make_test(model, 'state_stored_code')

        for model in (Model2,) + Model3AllDelegate:
            self.make_test(model, 'country_code2')
            self.make_test(model, 'partner_city')

        for model in (Model1, Model2) + Model3AllDelegate:
            self.make_test(model, 'country_code')

        # Demo user has access to Model3*, but not to Model2, Model1
        demo = self.env.ref('base.user_demo')
        self.assertTrue(demo.has_group('base.group_user'), 'Demo user is supposed to have Employee access rights')
        self.assertFalse(demo.has_group('base.group_system'), 'Demo user is not supposed to have Administrator access rights')
        # compute_sudo=False, auto_join=True
        model = Model3.with_user(demo)

        # Field path:
        # * related2_id (auto_join=True)
        # * related1_id (auto_join=False)
        # * partner_id (auto_join=False)
        # * state_id (auto_join=False)
        self.make_test(model, 'state_code')

        # Field path:
        # * related2_id (auto_join=True)
        # * test_read_group.related2::state_id (compute_sudo=True)
        # * related1_id (auto_join=False)
        # * partner_id (auto_join=False)
        # * state_id (auto_join=False)
        self.make_test(model, 'state_code2')

        # Only one join to parent Model and as we have auto_join, we are authorised to read it
        self.make_test(model, 'state_stored_code')

        # compute_sudo=False
        model = Model3NoSudo.with_user(demo)
        self.make_test(model, 'state_code')
        self.make_test(model, 'state_code2')
        self.make_test(model, 'state_stored_code')

        # compute_sudo=False, no _inherits
        model = Model3NoSudoNoDelegate.with_user(demo)
        with self.assertRaises(AccessError):
            self.make_test(model, 'state_code')
        with self.assertRaises(AccessError):
            self.make_test(model, 'state_code2')
        with self.assertRaises(AccessError):
            self.make_test(model, 'state_stored_code')

    def make_test(self, model, field):
        # Compute expected read_group result via search
        # field2vals = {field_value: [read_group_values]}
        field2vals = OrderedDict()
        for r in model.sudo().search([]):
            field_value = r[field]
            field2vals.setdefault(field_value, {
                '__domain': [(field, '=', field_value)],
                field: field_value,
                field + '_count': 0
            })
            field2vals[field_value][field + '_count'] += 1
        expected = list(field2vals.values())

        result = model.read_group([], [field], [field])
        self.assertEqual(expected, result)

        result = model.read_group([], [field], [field], orderby="%s desc" % field)
        expected.reverse()
        self.assertEqual(expected, result)
