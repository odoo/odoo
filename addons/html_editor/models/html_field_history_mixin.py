# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .diff_utils import apply_patch, generate_comparison, generate_patch, generate_unified_diff


class HtmlFieldHistoryMixin(models.AbstractModel):
    _name = 'html.field.history.mixin'
    _description = "Field html History"
    _html_field_history_size_limit = 300

    html_field_history = fields.Json("History data", prefetch=False)

    html_field_history_metadata = fields.Json(
        "History metadata", compute="_compute_metadata"
    )

    @api.model
    def _get_versioned_fields(self):
        """This method should be overriden

        :return: List[string]: A list of name of the fields to be versioned
        """
        return []

    @api.depends("html_field_history")
    def _compute_metadata(self):
        for rec in self:
            history_metadata = None
            if rec.html_field_history:
                history_metadata = {}
                for field_name in rec.html_field_history:
                    history_metadata[field_name] = []
                    for revision in rec.html_field_history[field_name]:
                        metadata = revision.copy()
                        metadata.pop("patch")
                        history_metadata[field_name].append(metadata)
            rec.html_field_history_metadata = history_metadata

    def write(self, vals):
        rec_db_contents = {}
        versioned_fields = self._get_versioned_fields()
        vals_contain_versioned_fields = set(vals).intersection(versioned_fields)

        if vals_contain_versioned_fields:
            for rec in self:
                rec_db_contents[rec.id] = {f: rec[f] for f in versioned_fields}

        # Call super().write before generating the patch to be sure we perform
        # the diff on sanitized data
        write_result = super().write(vals)

        if not vals_contain_versioned_fields:
            return write_result

        # allow mutlti record write
        for rec in self:
            new_revisions = False
            fields_data = self.env[rec._name]._fields

            if any(f in vals and not fields_data[f].sanitize for f in versioned_fields):
                raise ValidationError(  # pylint: disable=missing-gettext
                    "Ensure all versioned fields ( %s ) in model %s are declared as sanitize=True"
                    % (str(versioned_fields), rec._name)
                )

            history_revs = rec.html_field_history or {}

            for field in versioned_fields:
                new_content = rec[field] or ""

                if field not in history_revs:
                    history_revs[field] = []

                old_content = rec_db_contents[rec.id][field] or ""
                if new_content != old_content:
                    new_revisions = True
                    patch = generate_patch(new_content, old_content)
                    revision_id = (
                        (history_revs[field][0]["revision_id"] + 1)
                        if history_revs[field]
                        else 1
                    )

                    history_revs[field].insert(
                        0,
                        {
                            "patch": patch,
                            "revision_id": revision_id,
                            "create_date": self.env.cr.now().isoformat(),
                            "create_uid": self.env.uid,
                            "create_user_name": self.env.user.name,
                        },
                    )
                    limit = rec._html_field_history_size_limit
                    history_revs[field] = history_revs[field][:limit]
            # Call super().write again to include the new revision
            if new_revisions:
                extra_vals = {"html_field_history": history_revs}
                write_result = super(HtmlFieldHistoryMixin, rec).write(extra_vals) and write_result

        return write_result

    def html_field_history_get_content_at_revision(self, field_name, revision_id):
        """Get the requested field content restored at the revision_id.

        :param str field_name: the name of the field
        :param int revision_id: id of the last revision to restore

        :return: string: the restored content
        """
        self.ensure_one()
        revisions = [
            i
            for i in self.html_field_history[field_name]
            if i["revision_id"] >= revision_id
        ]

        content = self[field_name] or ""
        for revision in revisions:
            content = apply_patch(content, revision["patch"])

        return content

    def html_field_history_get_comparison_at_revision(self, field_name, revision_id):
        """For the requested field,
        Get a comparison between the current content of the field and the
        content restored at the requested revision_id.

        :param str field_name: the name of the field
        :param int revision_id: id of the last revision to compare

        :return: string: the comparison
        """
        self.ensure_one()
        restored_content = self.html_field_history_get_content_at_revision(
            field_name, revision_id
        )

        return generate_comparison(restored_content, self[field_name] or "")

    def html_field_history_get_unified_diff_at_revision(self, field_name, revision_id):
        """For the requested field,
        Get a unified diff between the current content of the field and the
        content restored at the requested revision_id.

        :param str field_name: the name of the field
        :param int revision_id: id of the last revision to compare

        :return: string: the unified diff
        """
        self.ensure_one()
        restored_content = self.html_field_history_get_content_at_revision(
            field_name, revision_id
        )

        return generate_unified_diff(self[field_name] or "", restored_content)
