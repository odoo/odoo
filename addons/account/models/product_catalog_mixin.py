# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductCatalogMixin(models.AbstractModel):
    _inherit = 'product.catalog.mixin'

    def _create_section(self, child_field, name, position, **kwargs):
        """Create a new section in order.

        :param str child_field: Field name of the order's lines (e.g., 'order_line').
        :param str name: The name of the section to create.
        :param str position: The position of the section where it should be created, either 'top'
                              or 'bottom'.
        :param dict kwargs: Additional values given for inherited models.

        :return: A dictionary with newly created section's 'id' and 'sequence'.
        :rtype: dict
        """
        parent_field = self._get_parent_field_on_child_model()

        if not parent_field:
            return {}

        lines = self[child_field].sorted('sequence')
        line_model = lines._name
        sequence = 10
        if lines:
            sequence = (
                lines[0].sequence - 1 if position == 'top'
                else lines[-1].sequence + 1
            )

        section = self.env[line_model].create({
            parent_field: self.id,
            'name': name,
            'display_type': 'line_section',
            'sequence': sequence,
            **self._get_default_create_section_values(),
        })

        return {
            'id': section.id,
            'sequence': section.sequence,
        }

    def _get_new_line_sequence(self, child_field, section_id):
        """Compute the sequence number for inserting a new line into the order.

        :param str child_field: Field name of the order's lines (e.g., 'order_line').
        :param int section_id: ID of the section line to insert after.
        :rtype: int
        :return: Computed sequence number.
        """
        lines = self[child_field].sorted('sequence')

        if section_id:
            # Insert after the selected section line
            sequence = lines.filtered_domain([
                ('display_type', '=', 'line_section'),
                ('id', '=', section_id),
            ]).sequence + 1
        elif (
            section_lines := lines.filtered_domain([
                ('display_type', '=', 'line_section'),
            ])
        ):
            # Insert before the first section (top of the order)
            sequence = section_lines[0].sequence
        else:
            # No sections exist, insert at the end
            sequence = (lines and lines[-1].sequence + 1) or 10

        for line in lines.filtered_domain([('sequence', '>=', sequence)]):
            line.sequence += 1

        return sequence

    def _get_sections(self, child_field, **kwargs):
        """Return section data for the product catalog display.

        :param str child_field: Field name of the order's lines (e.g., 'order_line').
        :param dict kwargs: Additional values given for inherited models.
        :rtype: list
        :return: List of section dicts with 'id', 'name', 'sequence', and 'line_count'.
        """
        sections = {}
        no_section_count = 0
        lines = self[child_field]
        for line in lines.sorted('sequence'):
            if line.display_type == 'line_section':
                sections[line.id] = {
                    'id': line.id,
                    'name': line.name,
                    'sequence': line.sequence,
                    'line_count': 0,
                }
            elif self._is_line_valid_for_section_line_count(line):
                sec_id = line.get_parent_section_line().id
                if sec_id and sec_id in sections:
                    sections[sec_id]['line_count'] += 1
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

    def _get_default_create_section_values(self):
        """Return default values for creating a new section in order through catalog.

        :return: A dictionary with default values for creating a new section.
        :rtype: dict
        """
        return {}

    def _get_parent_field_on_child_model(self):
        """Return the parent field for the order lines.

        :return: parent field
        :rtype: str
        """
        return ''

    def _is_line_valid_for_section_line_count(self, line):
        """Check if a line is valid for inclusion in the section's line count.

        :param recordset line: A record of an order line.
        :return: whether this line should be considered in the section lines count.
        :rtype: bool
        """
        return (
            not line.display_type
            and line.product_type != 'combo'
            and line.product_uom_qty > 0
        )

    def _resequence_sections(self, sections, child_field, **kwargs):
        """Resequence the order content based on the new sequence order.

        :param list sections: A list of dictionaries containing move and target sections.
        :param str child_field: Field name of the order's lines (e.g., 'order_line').
        :param dict kwargs: Additional values given for inherited models.
        :return: A dictonary containing the new sequences of all the sections of order.
        :rtype: dict
        """
        lines = self[child_field].sorted('sequence')
        move_section, target_section = sections

        move_block = lines.filtered(
            lambda line: line.id == move_section['id']
            or line.parent_id.id == move_section['id'],
        )

        target_block = lines.filtered(
            lambda line: line.id == target_section['id']
            or line.parent_id.id == target_section['id'],
        )

        remaining_lines = lines - move_block
        insert_after = move_section['sequence'] < target_section['sequence']
        insert_index = len(remaining_lines)
        for idx, line in enumerate(remaining_lines):
            if line.id == (target_block[-1].id if insert_after else target_section['id']):
                insert_index = idx + 1 if insert_after else idx
                break

        reordered_lines = (
            remaining_lines[:insert_index] +
            move_block +
            remaining_lines[insert_index:]
        )

        sections = {}
        for sequence, line in enumerate(reordered_lines, start=1):
            line.sequence = sequence
            if line.display_type == 'line_section':
                sections[line.id] = sequence

        return sections
