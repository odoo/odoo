# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import ValidationError


class ProductCatalogMixin(models.AbstractModel):
    _inherit = 'product.catalog.mixin'

    def _has_sections(self) -> bool:
        """Determine whether this model handles (sub)sections.

        Must be overridden to enable (sub)sections update in the catalog.
        """
        return False

    def _get_action_add_from_catalog_extra_context(self):
        res = super()._get_action_add_from_catalog_extra_context()

        if self._has_sections():
            res['show_sections'] = bool(self.id)

        return res

    def _get_product_catalog_record_lines(
        self, product_ids, child_field, *, section_id=None, **kwargs
    ):
        if not self._has_sections() or section_id:
            return super()._get_product_catalog_record_lines(
                product_ids, child_field, section_id=section_id, **kwargs
            )

        # If no particular section was chosen, use the first one by default (if any).
        first_child = self[child_field][:1]
        if first_child.display_type == 'line_section':
            section_id = first_child.id

        return super()._get_product_catalog_record_lines(
            product_ids, child_field, section_id=section_id, **kwargs
        )

    def _catalog_prepare_new_line_vals(self, child_field, *args, section_id=None, **kwargs) -> dict:
        vals = super()._catalog_prepare_new_line_vals(
            child_field, *args, section_id=section_id, **kwargs
        )

        if self._has_sections():
            vals['sequence'] = self._get_new_line_sequence(child_field, section_id)

        return vals

    def _create_section(self, child_field, name, position, **kwargs) -> dict:  # noqa: ARG002
        """Create a new section in order.

        :param str child_field: Field name of the order's lines (e.g., 'order_line').
        :param str name: The name of the section to create.
        :param str position: The position of the section where it should be created, either 'top'
                              or 'bottom'.
        :param dict kwargs: Additional values given for inherited models.

        :return: A dictionary with newly created section's 'id' and 'sequence'.
        """
        if not self._has_sections():
            raise ValidationError(self.env._("This model does not support (sub)sections"))

        parent_field = self._fields[child_field].inverse_name

        lines = self[child_field].sorted('sequence')
        line_model = lines._name
        sequence = 10
        if lines:
            sequence = lines[0].sequence - 1 if position == 'top' else lines[-1].sequence + 1

        section = self.env[line_model].create({
            parent_field: self.id,
            'name': name,
            'display_type': 'line_section',
            'sequence': sequence,
            lines._get_quantity_field(): 0,
        })

        return section.read(['id', 'sequence'])[0]

    def _get_new_line_sequence(self, child_field, section_id) -> int:
        """Compute the sequence number for inserting a new line into the order.

        :param str child_field: name of the one2many field holding the catalog lines.
        :param int section_id: ID of the section line to insert after.
        :return: Computed sequence number.
        """
        lines = self[child_field].sorted('sequence')

        # Default case : insert at the end
        sequence = (lines and lines[-1].sequence + 1) or 10
        if section_id:
            # Insert after the last product of the selected section
            section_found = False
            for line in lines:
                if line.display_type != 'line_section':
                    continue
                if section_found:
                    sequence = line.sequence
                    break
                if line.id == section_id:
                    section_found = True
        elif section_lines := lines.filtered_domain([('display_type', '=', 'line_section')]):
            # Insert before the first section (top of the order)
            sequence = section_lines[0].sequence

        for line in lines.filtered_domain([('sequence', '>=', sequence)]):
            line.sequence += 1

        return sequence

    def _get_sections(self, child_field, **kwargs) -> list[dict]:  # noqa: ARG002
        """Return section data for the product catalog display.

        :param str child_field: name of the one2many field holding the catalog lines.
        :param dict kwargs: Additional values given for inherited models.
        :return: List of section dicts with 'id', 'name', 'sequence', and 'line_count'.
        """
        sections = {}
        no_section_count = 0
        lines = self[child_field]
        qty_field = lines._get_quantity_field()
        section_id = False
        for line in lines.sorted('sequence'):
            if line.display_type == 'line_section':
                section_id = line.id
                sections[line.id] = {
                    'id': line.id,
                    'name': line.name,
                    'sequence': line.sequence,
                    'line_count': 0,
                }
            elif (
                line._consider_in_catalog(parent_record=self, section_id=section_id)
                and line[qty_field] > 0
            ):
                if section_id and section_id in sections:
                    sections[section_id]['line_count'] += 1
                else:
                    no_section_count += 1

        if no_section_count > 0 or not sections:
            # If there are products outside of a section or no section at all
            sections[False] = {
                'id': False,
                'name': self.env._("No Section"),
                'sequence': lines[0].sequence - 1 if lines else 0,
                'line_count': no_section_count,
            }

        return sorted(sections.values(), key=lambda x: x['sequence'])

    def _resequence_sections(self, sections, child_field, **kwargs) -> dict:  # noqa: ARG002
        """Resequence the order content based on the new sequence order.

        :param list sections: A list of dictionaries containing move and target sections.
        :param str child_field: name of the one2many field holding the catalog lines.
        :param dict kwargs: Additional values given for inherited models.
        :return: A dictionary containing the new sequences of all the sections of order.
        """
        lines = self[child_field].sorted('sequence')
        move_section, target_section = sections

        move_block = lines.filtered(
            lambda line: line.id == move_section['id'] or line.parent_id.id == move_section['id']
        )

        target_block = lines.filtered(
            lambda line: (
                line.id == target_section['id'] or line.parent_id.id == target_section['id']
            )
        )

        remaining_lines = lines - move_block
        insert_after = move_section['sequence'] < target_section['sequence']
        insert_index = len(remaining_lines)
        for idx, line in enumerate(remaining_lines):
            if line.id == (target_block[-1].id if insert_after else target_section['id']):
                insert_index = idx + 1 if insert_after else idx
                break

        reordered_lines = (
            remaining_lines[:insert_index] + move_block + remaining_lines[insert_index:]
        )

        sections = {}
        for sequence, line in enumerate(reordered_lines, start=1):
            line.sequence = sequence
            if line.display_type == 'line_section':
                sections[line.id] = sequence

        return sections
