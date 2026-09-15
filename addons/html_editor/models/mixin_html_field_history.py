from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog

from .diff_utils import (
    apply_patch,
    generate_comparison,
    generate_patch,
    generate_unified_diff,
)

_debug = DebugLog(__name__)


class MixinHtmlFieldHistory(models.AbstractModel):
    _name = "mixin.html.field.history"
    _description = "Field html History"
    _html_field_history_size_limit = 300

    html_field_history = fields.Json(
        string="History data",
        readonly=True,
        prefetch=False,
    )

    html_field_history_metadata = fields.Json(
        string="History metadata",
        compute="_compute_metadata",
    )

    @api.model
    def _get_fields_versioned(self):
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
                        metadata.pop("patch", None)
                        history_metadata[field_name].append(metadata)
            rec.html_field_history_metadata = history_metadata

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.pop("html_field_history", None)
        return super().create(vals_list)

    def write(self, vals):
        rec_db_contents = {}
        if "html_field_history" in vals:
            del vals["html_field_history"]
        versioned_fields = self._get_fields_versioned()
        vals_contain_versioned_fields = set(vals).intersection(versioned_fields)

        if vals_contain_versioned_fields:
            for rec in self:
                rec_db_contents[rec.id] = {f: rec[f] for f in versioned_fields}

        write_result = super().write(vals)

        if not vals_contain_versioned_fields:
            return write_result

        fields_data = self._fields
        if any(f in vals and not fields_data[f].sanitize for f in versioned_fields):
            _debug.logic(
                "history_refused",
                reason="unsanitized_versioned_field",
                model=self._name,
                fields=sorted(versioned_fields),
            )
            raise ValidationError(  # pylint: disable=missing-gettext
                "Ensure all versioned fields ( %s ) in model %s are declared as sanitize=True"
                % (str(versioned_fields), self._name)
            )

        for rec in self:
            new_revisions = False

            history_revs = {
                name: list(revisions)
                for name, revisions in (rec.html_field_history or {}).items()
            }

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
            if new_revisions:
                extra_vals = {"html_field_history": history_revs}
                write_result = (
                    super(MixinHtmlFieldHistory, rec).write(extra_vals) and write_result
                )

        return write_result

    def _check_versioned_field(self, field_name):
        if field_name not in self._get_fields_versioned():
            _debug.logic("history_field_refused", model=self._name, field=field_name)
            raise UserError(
                _(
                    'Field "%(field)s" is not versioned on model "%(model)s".',
                    field=field_name,
                    model=self._name,
                )
            )

    def _check_revision_id(self, revision_id):
        if isinstance(revision_id, bool) or not isinstance(revision_id, int):
            _debug.logic(
                "history_revision_refused", reason="not_an_int", model=self._name
            )
            raise UserError(
                _(
                    'Invalid revision id "%(revision)s": expected an integer.',
                    revision=revision_id,
                )
            )

    def html_field_history_get_content_at_revision(self, field_name, revision_id):
        self.check_singleton()
        self._check_versioned_field(field_name)
        self._check_revision_id(revision_id)
        revisions = [
            i
            for i in (self.html_field_history or {}).get(field_name) or []
            if i["revision_id"] >= revision_id
        ]

        content = self[field_name] or ""
        for revision in revisions:
            content = apply_patch(content, revision["patch"])

        return content

    def html_field_history_get_comparison_at_revision(self, field_name, revision_id):
        self.check_singleton()
        self._check_versioned_field(field_name)
        self._check_revision_id(revision_id)
        restored_content = self.html_field_history_get_content_at_revision(
            field_name, revision_id
        )

        return generate_comparison(restored_content, self[field_name] or "")

    def html_field_history_get_unified_diff_at_revision(self, field_name, revision_id):
        self.check_singleton()
        self._check_versioned_field(field_name)
        self._check_revision_id(revision_id)
        restored_content = self.html_field_history_get_content_at_revision(
            field_name, revision_id
        )

        return generate_unified_diff(self[field_name] or "", restored_content)
