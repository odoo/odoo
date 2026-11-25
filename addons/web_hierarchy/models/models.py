from odoo import api, models


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.readonly
    @api.model
    def hierarchy_read(self, domain, specification, parent_field_name, limit=None):
        field = self._fields.get(parent_field_name)
        if not field or field.type != 'many2one' or field.comodel_name != self._name:
            raise ValueError(f"Invalid parent field {parent_field_name!r} for {self._name}")

        records = self.search_fetch(domain, [parent_field_name])
        ids = set(records._ids)

        roots = []
        children = {record_id: [] for record_id in records._ids}
        for record in records:
            parent_id = record[parent_field_name].id
            if parent_id and parent_id != record.id and parent_id in ids:
                children[parent_id].append(record.id)
            else:
                roots.append(record.id)

        reached = set()

        def visit(root_id):
            reached.add(root_id)
            stack = [root_id]
            while stack:
                node_id = stack.pop()
                kept = [child_id for child_id in children[node_id] if child_id not in reached]
                children[node_id] = kept
                reached.update(kept)
                stack.extend(kept)

        for root_id in roots:
            visit(root_id)

        cycle_roots = []
        for record_id in records._ids:
            if record_id not in reached:
                cycle_roots.append(record_id)
                visit(record_id)
        roots += cycle_roots

        children_by_parent = {False: roots, **children}
        opened = []
        queue = [False]
        i = 0
        remaining = len(ids) if limit is None else limit
        while i < len(queue) and remaining > 0:
            parent_id = queue[i]
            i += 1
            if child_ids := children_by_parent[parent_id]:
                child_ids.sort(key=lambda child_id: len(children[child_id]), reverse=True)
                taken = child_ids[:remaining]
                remaining -= len(taken)
                opened.append((parent_id, taken))
                queue.extend(taken)

        selected = [record_id for __, taken in opened for record_id in taken]
        return {
            'records': self.browse(selected).web_read(specification),
            'length': len(ids),
            'children': opened,
        }
