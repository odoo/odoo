import base64

import polib

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_list


class Resource(models.Model):
    _name = "t9n.resource"
    _description = "Resource file"

    file_name = fields.Char()
    file = fields.Binary("Resource File", store=False)
    message_ids = fields.One2many(
        comodel_name="t9n.message",
        inverse_name="resource_id",
        string="Entries to translate",
    )
    project_id = fields.Many2one(
        comodel_name="t9n.project",
    )

    _sql_constraints = [
        (
            "file_name_project_id_unique",
            "unique(file_name, project_id)",
            "A file with the same name already exists in the same project.",
        ),
    ]

    def _decode_resource_file(self, resource_file):
        try:
            file_content = base64.b64decode(resource_file).decode()
            po_obj = polib.pofile(file_content)
        except (IOError, UnicodeDecodeError):
            po_obj = []
        return [
            {
                "body": entry.msgid,
                "context": entry.msgctxt,
                "translator_comments": entry.tcomment,
                "extracted_comments": entry.comment,
                "references": "\n".join([fpath + (lineno and f":{lineno}") for fpath, lineno in entry.occurrences]),
            }
            for entry in po_obj
        ]

    @api.model_create_multi
    def create(self, vals_list):
        broken_files = []
        for vals in vals_list:
            if not vals.get("file"):
                raise ValidationError(_("A resource file is required to create a resource."))
            po_obj = self._decode_resource_file(vals["file"])
            del vals["file"]
            if not po_obj:
                broken_files.append(vals["file_name"])
                continue
            vals["message_ids"] = [Command.create(message) for message in po_obj]
        if broken_files:
            raise UserError(
                _(
                    "Resource files must be valid .pot files. The following files are ill-formatted or empty: %(file_names)s",
                    file_names=format_list(self.env, broken_files),
                ),
            )
        return super().create(vals_list)

    def write(self, vals):
        self.ensure_one()
        if "file" not in vals:
            return super().write(vals)
        po_obj = self._decode_resource_file(vals["file"])
        del vals["file"]
        if not po_obj:
            raise UserError(
                _("The files: %(file_name)s should be a .po file with a valid syntax.", file_name=vals["file_name"]),
            )
        current_msgs_by_tuple = {(msg.body, msg.context): msg for msg in self.message_ids}
        new_msgs_by_tuple = {(msg["body"], msg["context"]): msg for msg in po_obj}
        to_create = [msg_val for key, msg_val in new_msgs_by_tuple.items() if key not in current_msgs_by_tuple]
        to_unlink = {msg.id for key, msg in current_msgs_by_tuple.items() if key not in new_msgs_by_tuple}
        to_update = [
            (current_msgs_by_tuple[key].id, new_msgs_by_tuple[key])
            for key in set(current_msgs_by_tuple) & set(new_msgs_by_tuple)
        ]
        vals["message_ids"] = (
            [Command.create(vals) for vals in to_create]
            + [Command.unlink(id) for id in to_unlink]
            + [Command.update(id, vals) for id, vals in to_update]
        )
        return super().write(vals)
