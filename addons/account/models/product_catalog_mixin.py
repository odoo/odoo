# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductCatalogMixin(models.AbstractModel):
    _inherit = 'product.catalog.mixin'

    def _create_section(self, child_field, name, position, parent_id=None, **kwargs):
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
        if parent_id:
            # creating subsection
            parent_line = lines.filtered(lambda l: l.id == parent_id)

            next_section = lines.filtered(
                lambda l: l.display_type == 'line_section'
                and l.sequence > parent_line.sequence
            )[:1]

            if next_section:
                sequence = next_section.sequence - 1
            else:
                # No next section → put at end
                sequence = lines[-1].sequence + 1 if lines else 10

            display_type = 'line_subsection'

        else:
            # creating section
            sequence = 10
            if lines:
                sequence = (
                    lines[0].sequence - 1 if position == 'top'
                    else lines[-1].sequence + 1
                )

            display_type = 'line_section'

        section = self.env[line_model].create({
            parent_field: self.id,
            'name': name,
            'display_type': display_type,
            'sequence': sequence,
            **self._get_default_create_section_values(),
        })

        return {
            'id': section.id,
            'sequence': section.sequence,
            'display_type': display_type,
            'subtotal': 0.0,
            'currency_id': self.currency_id.id,
            'collapse_prices': False, #update
            'collapse_composition': False, #update
            'is_optional': False, #update
        }

    def _get_new_line_sequence(self, child_field, section_id):
        """Compute the sequence number for inserting a new line into the order.

        :param str child_field: Field name of the order's lines (e.g., 'order_line').
        :param int section_id: ID of the section line to insert after.
        :rtype: int
        :return: Computed sequence number.
        """
        lines = self[child_field].sorted('sequence')

        # Default case : insert at the end
        sequence = (lines and lines[-1].sequence + 1) or 10
        if section_id:
            # Insert after the last product of the selected section
            section_found = False
            for line in lines:
                if line.display_type not in ('line_section', 'line_subsection'):
                    continue
                if section_found:
                    sequence = line.sequence
                    break
                if line.id == section_id:
                    section_found = True
        elif (
            section_lines := lines.filtered_domain([
                ('display_type', '=', 'line_section'),
            ])
        ):
            # Insert before the first section (top of the order)
            sequence = section_lines[0].sequence

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
        no_section_subtotal = 0.0
        lines = self[child_field]
        for line in lines.sorted('sequence'):
            if line.display_type in ('line_section', 'line_subsection'):
                values = {
                    'id': line.id,
                    'name': line.name,
                    'sequence': line.sequence,
                    'parent_id': line.parent_id.id if line.display_type == 'line_subsection' else False,
                    'line_count': 0,
                    'display_type': line.display_type,
                    'subtotal': line._get_section_totals('price_subtotal'),
                    'currency_id': self.currency_id.id,
                }
                if hasattr(line, 'collapse_prices'):
                    values['collapse_prices'] = line.collapse_prices
                if hasattr(line, 'collapse_composition'):
                    values['collapse_composition'] = line.collapse_composition
                if hasattr(line, 'is_optional'):
                    values['is_optional'] = line.is_optional
                sections[line.id] = values
            elif self._is_line_valid_for_section_line_count(line):
                if line.parent_id and line.parent_id.id in sections:
                    sections[line.parent_id.id]['line_count'] += 1

                if line.parent_id and line.parent_id.parent_id and line.parent_id.parent_id.id in sections:
                    sections[line.parent_id.parent_id.id]['line_count'] += 1

                if not line.parent_id:
                    no_section_count += 1
                    no_section_subtotal += line.price_subtotal

        if no_section_count > 0 or not sections:
            # If there are products outside of a section or no section at all
            sections[False] = {
                'id': False,
                'name': self.env._("No Section"),
                'sequence': lines[0].sequence - 1 if lines else 0,
                'parent_id': False,
                'line_count': no_section_count,
                'display_type': False,
                'subtotal': no_section_subtotal,
                'currency_id': self.currency_id.id,
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

    def _resequence_sections(self, child_field, id, parent_id, before_id=None, **kwargs):
        lines = self[child_field].sorted("sequence")
        section = lines.browse(id)

        if not section:
            return True

        # 1. GET SUBTREE (CONTIGUOUS BLOCK)
        def _get_subtree(node, ordered_lines):
            result = self.env[node._name].browse()
            collecting = False
            parent_stack = {node.id}

            for line in ordered_lines:
                if line.id == node.id:
                    collecting = True
                    result |= line
                    continue

                if not collecting:
                    continue

                if line.parent_id.id in parent_stack:
                    result |= line
                    parent_stack.add(line.id)
                else:
                    break

            return result

        subtree = _get_subtree(section, lines)

        # 2. PREVENT CYCLIC MOVE
        if parent_id and parent_id in subtree.ids:
            return True

        # 3. REMOVE SUBTREE FROM LIST
        remaining = lines - subtree

        # 4. UPDATE PARENT
        section.parent_id = parent_id or False

        # 5. COMPUTE INSERT INDEX
        insert_index = None

        # CASE 1: use before_id (highest priority)
        if before_id:
            for i, line in enumerate(remaining):
                if line.id == before_id:
                    insert_index = i
                    break

        # CASE 2: insert inside parent (as last child)
        elif parent_id:
            parent = lines.browse(parent_id)
            parent_subtree = _get_subtree(parent, lines)
            last_line = parent_subtree[-1]

            for i, line in enumerate(remaining):
                if line.id == last_line.id:
                    insert_index = i + 1
                    break

        # CASE 3: fallback
        if insert_index is None:
            insert_index = len(remaining)

        # 6. NORMALIZE ROOT INSERTION
        if not parent_id:
            if insert_index < len(remaining):
                next_line = remaining[insert_index]

                if next_line.parent_id:
                    ancestor = next_line
                    while ancestor.parent_id:
                        ancestor = ancestor.parent_id

                    for i, line in enumerate(remaining):
                        if line.id == ancestor.id:
                            insert_index = i
                            break

        # 7. BUILD FINAL ORDER
        new_list = (
            remaining[:insert_index]
            | subtree
            | remaining[insert_index:]
        )

        # 8. RESEQUENCE FULL ORDER
        for seq, line in enumerate(new_list, start=1):
            line.sequence = seq

        # 9. NORMALIZE DISPLAY TYPE
        if not parent_id:
            section.display_type = 'line_section'
        else:
            section.display_type = 'line_subsection'

        return True

    def _duplicate_section(self, child_field, section_id, parent_id=None, **kwargs):
        """Duplicate the given section with all its children."""
        lines = self[child_field]

        if parent_id:
            section_lines = lines.filtered(
                lambda l: l.id == section_id or l.parent_id.id == section_id
            )
        else:
            section_lines = lines.filtered(
                lambda l: l.id == section_id
                or l.get_parent_section_line().id == section_id
            )

        section_lines = section_lines.sorted("sequence")

        # --- Anchor = last line of block ---
        anchor = section_lines[-1]

        # --- Stable ordering (sequence, id) ---
        ordered_lines = lines.sorted(lambda l: (l.sequence, l.id))

        # --- Find anchor index ---
        anchor_index = ordered_lines.ids.index(anchor.id)

        # --- Lines AFTER anchor (including same sequence ones) ---
        to_shift = ordered_lines[anchor_index + 1:]

        shift_by = len(section_lines) + 1

        # --- Shift sequences (make space) ---
        for line in to_shift:
            line.sequence += shift_by

        # --- Insert duplicated block ---
        base_sequence = anchor.sequence + 1

        commands = []
        for i, line in enumerate(section_lines):
            vals = line.copy_data()[0]
            vals["sequence"] = base_sequence + i
            commands.append((0, 0, vals))

        existing_ids = set(lines.ids)

        self.write({child_field: commands})

        new_section = self[child_field].filtered(lambda l: l.id not in existing_ids).sorted("sequence")[0]

        # return sequences of all sections to update the view and new section id for selection
        return {
            "sections": {
                line.id: line.sequence
                for line in lines
                if line.display_type in ("line_section", "line_subsection")
            },
            "id": new_section.id,
        }

    def _delete_section(self, child_field, section_id, **kwargs):
        lines = self[child_field]
        section = lines.browse(section_id)

        if not section:
            return True

        # --- Find all lines to delete (section + children) ---
        if section.display_type == 'line_section':
            to_delete = lines.filtered(
                lambda l: l.id == section_id
                or l.get_parent_section_line().id == section_id
            )
        else:
            to_delete = lines.filtered(
                lambda l: l.id == section_id
                or l.parent_id.id == section_id
            )

        to_delete.unlink()

        return True

    def _toggle_field_of_section(self, child_field, section_id, field_name, **kwargs):
        lines = self[child_field]
        section = lines.browse(section_id)

        if not section.exists():
            return True

        # ensure field exists on model
        if field_name not in section._fields:
            return True

        section[field_name] = not section[field_name]

        return True
