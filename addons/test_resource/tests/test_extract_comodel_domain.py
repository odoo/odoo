# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain
from odoo.tests import TransactionCase, tagged

from odoo.addons.resource.models.utils import extract_comodel_domain


@tagged('-at_install', 'post_install')
class TestExtractComodelDomain(TransactionCase):
    def test_convert_model_name(self):
        """
        comparing on relation id should compare on name/display_name
        """
        model = self.env['related.resource.test.2']
        field_expr = 'related_resource_test_id'
        domain = Domain('related_resource_test_id', '=', 'Moxxie')
        wanted_domain = Domain('name', 'in', ['Moxxie'])
        self.assertEqual(
            tuple(extract_comodel_domain(model, domain, field_expr)),
            tuple(wanted_domain),
        )

    def test_convert_model_field_prefix(self):
        """
        base case, 'relation_field.field' should just resolve to 'field'
        """
        model = self.env['related.resource.test.2']
        field_expr = 'related_resource_test_1_id'
        domain = Domain('related_resource_test_1_id.surname', '=', 'Moxxie')
        wanted_domain = Domain('surname', 'in', ['Moxxie'])
        self.assertEqual(
            tuple(extract_comodel_domain(model, domain, field_expr)),
            tuple(wanted_domain),
        )

    def test_convert_model_irrelevant_field(self):
        """
        fields that are not part of the comodel should be removed
        """
        model = self.env['related.resource.test.2']
        field_expr = 'related_resource_test_1_id'
        domain = Domain('profile_picture', '=', False)
        wanted_domain = Domain.TRUE
        self.assertEqual(
            tuple(extract_comodel_domain(model, domain, field_expr)),
            tuple(wanted_domain),
        )

    def test_convert_model_non_existant_field(self):
        """
        Fields that simply don't exist should raise an error
        """
        model = self.env['related.resource.test.2']
        field_expr = 'related_resource_test_1_id'
        domain = Domain('field_that_does_not_exist', '=', 4)
        with self.assertRaises(ValueError):
            extract_comodel_domain(model, domain, field_expr)

    def test_convert_model_related_no_prefix(self):
        """
        size_related_2 is related to related_resource_test_1_id.size_related
        which is also related to resource_test_id.size
        So in the end we should get resource_test_id.size (with "any!" due to
        the internal use of optimize_full()
        """
        model = self.env['related.resource.test.2']
        field_expr = 'related_resource_test_1_id'
        domain = Domain('size_related_2', '>', 3)
        wanted_domain = Domain('resource_test_id', 'any!', [('size', '>', 3)])
        self.assertEqual(
            tuple(extract_comodel_domain(model, domain, field_expr)),
            tuple(wanted_domain),
        )

    def test_convert_model_related_basic(self):
        """
        is_valid_related is a related to related_resource_test_1_id.is_valid
        so the function should simply resolve to is_valid
        """
        model = self.env['related.resource.test.2']
        field_expr = 'related_resource_test_1_id'
        domain = Domain('is_valid_related', '=', True)
        wanted_domain = Domain('is_valid', 'in', [True])
        self.assertEqual(
            tuple(extract_comodel_domain(model, domain, field_expr)),
            tuple(wanted_domain),
        )

    def test_convert_model_related_wrong_field(self):
        """
        name_related_orig is a related to an irrelevant model.
        It should thus be ignored.
        """
        model = self.env['related.resource.test.2']
        field_expr = 'related_resource_test_1_id'
        domain = Domain('name_related_orig', '=', True)
        wanted_domain = Domain.TRUE
        self.assertEqual(
            tuple(extract_comodel_domain(model, domain, field_expr)),
            tuple(wanted_domain),
        )

    def test_convert_model_recursive_id(self):
        """
        related_resource_test_id is by itself a related field. The function
        should still be able to treat it normally in that case
        """
        model = self.env['related.resource.test.2']
        field_expr = 'related_resource_test_id'
        domain = Domain('related_resource_test_id.size', '>', 3)
        wanted_domain = Domain('size', '>', 3)
        self.assertEqual(
            tuple(extract_comodel_domain(model, domain, field_expr)),
            tuple(wanted_domain),
        )

    def test_convert_model_recursive(self):
        """
        related_resource_test_id is the same (related) as
        "related_resource_test_1_id.resource_test_id", so it should also be able
        to convert fields starting with
        "related_resource_test_1_id.resource_test_id"
        """
        model = self.env['related.resource.test.2']
        field_expr = 'related_resource_test_id'
        domain = Domain(
            'related_resource_test_1_id.resource_test_id.size',
            '>',
            3,
        )
        wanted_domain = Domain('size', '>', 3)
        self.assertEqual(
            tuple(extract_comodel_domain(model, domain, field_expr)),
            tuple(wanted_domain),
        )

    def test_extract_comodel_domain_multiple_conditions(self):
        model = self.env['related.resource.test.2']
        field_expr = 'related_resource_test_id'

        # both are the same - will only keep "name"
        domain = Domain('related_resource_test_id', '=', 'Moxxie')
        domain &= Domain('related_resource_test_1_id.surname', '=', 'Moxxie')
        wanted_domain = Domain('name', 'in', ['Moxxie'])
        wanted_domain &= Domain('surname', 'in', ['Moxxie'])
        domain &= Domain('profile_picture', '=', False)  # should be ignored
        domain |= Domain('size_related_2', '>', 3)
        # not in related_resource_test_id - ignored
        domain |= Domain('is_valid_related', '=', True)
        domain &= Domain('name_related_orig', '=', True)  # should be ignored
        wanted_domain = Domain.OR(
            [
                Domain('name', 'in', ['Moxxie']),
                Domain('size', '>', 3),
            ],
        )
        self.assertEqual(
            tuple(extract_comodel_domain(model, domain, field_expr)),
            tuple(wanted_domain),
            """
            extract_comodel_domain() did not return the converted, optimized
            model that is usable on the comodel pointed by the field_expr
            'related_resource_test_id'
            """,
        )
