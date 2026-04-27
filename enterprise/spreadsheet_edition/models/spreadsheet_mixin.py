# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import base64
import psycopg2
import uuid

from datetime import timedelta
from typing import Dict, Any, List, Optional

from odoo import _, fields, models, api
from odoo.exceptions import AccessError, UserError
from odoo.tools import mute_logger, OrderedSet, image_process

_logger = logging.getLogger(__name__)

CollaborationMessage = Dict[str, Any]


class SpreadsheetMixin(models.AbstractModel):
    _name = "spreadsheet.mixin"
    _inherit = ["spreadsheet.mixin", "bus.listener.mixin"]

    spreadsheet_snapshot = fields.Binary()
    display_thumbnail = fields.Binary(compute='_compute_display_thumbnail', inverse='_inverse_display_thumbnail')
    spreadsheet_revision_ids = fields.One2many(
        "spreadsheet.revision",
        "res_id",
        domain=lambda self: [('res_model', '=', self._name)],
        groups="base.group_system",
    )
    # The last revision id known by the current transaction.
    # Another concurrent transaction can have saved a revision after this one
    # This means it cannot be blindly used to dispatch a new revision.
    current_revision_uuid = fields.Char(compute="_compute_current_revision_uuid", compute_sudo=True)

    @api.depends("spreadsheet_revision_ids", "spreadsheet_snapshot", "spreadsheet_data")
    def _compute_current_revision_uuid(self):
        for spreadsheet in self:
            revisions = spreadsheet.spreadsheet_revision_ids
            if revisions:
                revisions.fetch(["revision_uuid"])
                spreadsheet.current_revision_uuid = revisions[-1].revision_uuid
            else:
                snapshot = spreadsheet._get_spreadsheet_snapshot()
                if snapshot is False:
                    spreadsheet.current_revision_uuid = False
                else:
                    spreadsheet.current_revision_uuid = snapshot.get("revisionId", "START_REVISION")

    def write(self, vals):
        if "spreadsheet_binary_data" in vals and not self.env.context.get("preserve_spreadsheet_revisions"):
            self._delete_collaborative_data()
        return super().write(vals)

    def copy(self, default=None):
        default = default or {}
        new_spreadsheets = super().copy(default)
        is_data_changed = bool(default.keys() & {"spreadsheet_data", "spreadsheet_binary_data"})
        if not is_data_changed:
            if "spreadsheet_revision_ids" not in default:
                for old_spreadsheet, new_spreadsheet in zip(self, new_spreadsheets):
                    old_spreadsheet._copy_revisions_to(new_spreadsheet)
            new_spreadsheets = new_spreadsheets.with_context(preserve_spreadsheet_revisions=True)
            for old_spreadsheet, new_spreadsheet in zip(self, new_spreadsheets):
                new_spreadsheet.spreadsheet_data = old_spreadsheet.spreadsheet_data
        new_spreadsheets._copy_spreadsheet_image_attachments()
        new_spreadsheets._delete_comments_from_data()
        return new_spreadsheets

    @api.model_create_multi
    def create(self, vals_list):
        spreadsheets = super().create(vals_list)
        spreadsheets._copy_spreadsheet_image_attachments()
        return spreadsheets

    def join_spreadsheet_session(self, access_token=None):
        """Join a spreadsheet session.
        Returns the following data::
        - the last snapshot
        - pending revisions since the last snapshot
        - the spreadsheet name
        - whether the user favorited the spreadsheet or not
        - whether the user can edit the content of the spreadsheet or not
        """
        self.ensure_one()
        self._check_collaborative_spreadsheet_access("read", access_token)
        can_write = self._check_collaborative_spreadsheet_access(
            "write", access_token, raise_exception=False
        )
        spreadsheet_sudo = self.sudo()
        return {
            "id": spreadsheet_sudo.id,
            "name": spreadsheet_sudo.display_name or "",
            "data": spreadsheet_sudo._get_spreadsheet_snapshot(),
            "revisions": spreadsheet_sudo._build_spreadsheet_messages(),
            "snapshot_requested": can_write and spreadsheet_sudo._should_be_snapshotted(),
            "isReadonly": not can_write,
            "default_currency": self.env["res.currency"].get_company_currency_for_spreadsheet(),
            "user_locale": self.env["res.lang"]._get_user_spreadsheet_locale(),
            "company_colors": self._get_context_company_colors(),
            "writable_rec_name_field": self._get_writable_record_name_field(),
        }

    def dispatch_spreadsheet_message(self, message: CollaborationMessage, access_token=None):
        """This is the entry point of collaborative editing.
        Collaboration messages arrive here. For each received messages,
        the server decides if it's accepted or not. If the message is
        accepted, it's transmitted to all clients through the "bus.bus".
        Messages which do not update the spreadsheet state (a client moved
        joined or left) are always accepted. Messages updating the state
        require special care.

        Refused messages
        ----------------

        An important aspect of collaborative messages is their order. The server
        checks the order of received messages. If one is out of order, it is refused.
        How does it check the order?
        Each message has a `serverRevisionId` property which is the revision on which
        it should be applied. If it's not equal to the current known revision by the server,
        it is out of order and refused.

        Accepted messages
        -----------------

        If the message is found to be in order, it's accepted and the server registers it.
        The current server revision becomes the revision carried by the message, in the
        `nextRevisionId` property.
        With this strategy, we are guaranteed that all accepted message are ordered.
        See `_spreadsheet_revision_is_accepted`.

        :param message: collaborative message to process
        :return: if the message was accepted or not.
        :rtype: bool
        """
        self.ensure_one()

        if message["type"] in ["REMOTE_REVISION", "REVISION_UNDONE", "REVISION_REDONE"]:
            self._check_collaborative_spreadsheet_access("write", access_token)
            is_accepted = self.sudo()._save_concurrent_revision(
                message["nextRevisionId"],
                message["serverRevisionId"],
                self._build_spreadsheet_revision_data(message),
            )
            if is_accepted:
                self._broadcast_spreadsheet_message(message)
            return is_accepted
        elif message["type"] == "SNAPSHOT":
            self._check_collaborative_spreadsheet_access("write", access_token)
            return self.sudo()._snapshot_spreadsheet(
                message["serverRevisionId"], message["nextRevisionId"], message["data"]
            )
        elif message["type"] in ["CLIENT_JOINED", "CLIENT_LEFT", "CLIENT_MOVED"]:
            self._check_collaborative_spreadsheet_access("read", access_token)
            self._broadcast_spreadsheet_message(message)
            return True
        return False

    def _copy_revisions_to(self, spreadsheet, up_to_revision_id=False):
        self._check_collaborative_spreadsheet_access("read")
        if up_to_revision_id:
            revisions = self.sudo().spreadsheet_revision_ids.filtered(
                lambda r: r.id <= up_to_revision_id
            )
        else:
            revisions = self.sudo().with_context(active_test=False).spreadsheet_revision_ids
        copied_revisions = self.env["spreadsheet.revision"]
        parent_revision = self.env["spreadsheet.revision"]
        for revision in revisions:
            commands = self._delete_comments_from_commands(revision.commands)
            parent_revision = revision.copy({
                "res_model": spreadsheet._name,
                "res_id": spreadsheet.id,
                "parent_revision_id": parent_revision.id,
                "commands": commands,
            })
            copied_revisions |= parent_revision
        spreadsheet._check_collaborative_spreadsheet_access("write")
        spreadsheet.sudo().spreadsheet_revision_ids = copied_revisions

    def save_spreadsheet_snapshot(self, snapshot_data):
        data_revision_uuid = snapshot_data.get("revisionId")
        snapshot_uuid = str(uuid.uuid4())
        snapshot_data["revisionId"] = snapshot_uuid
        revision = {
            "type": "SNAPSHOT",
            "serverRevisionId": data_revision_uuid,
            "nextRevisionId": snapshot_uuid,
            "data": snapshot_data,
        }
        is_accepted = self.dispatch_spreadsheet_message(revision)
        if not is_accepted:
            raise UserError(_("The operation could not be applied because of a concurrent update. Please try again."))

    def _snapshot_spreadsheet(
        self, revision_uuid: str, snapshot_revision_uuid, spreadsheet_snapshot: dict
    ):
        """Save the spreadsheet snapshot along the revision id. Delete previous
        revisions which are no longer needed.
        If the `revision_uuid` is not the same as the server revision, the snapshot is
        not accepted and is ignored.

        :param revision_uuid: the revision on which the snapshot is based
        :param snapshot_revision_uuid: snapshot revision
        :param spreadsheet_snapshot: spreadsheet data
        :return: True if the snapshot was saved, False otherwise
        """
        if snapshot_revision_uuid != spreadsheet_snapshot.get("revisionId"):
            raise ValueError("The snapshot revision id does not match the revision id")

        is_accepted = self._save_concurrent_revision(
            snapshot_revision_uuid,
            revision_uuid,
            {"type": "SNAPSHOT_CREATED", "version": 1},
        )
        if is_accepted:
            self.spreadsheet_snapshot = base64.b64encode(
                json.dumps(spreadsheet_snapshot).encode()
            )
            self.spreadsheet_revision_ids.active = False
            self._broadcast_spreadsheet_message(
                {
                    "type": "SNAPSHOT_CREATED",
                    "serverRevisionId": revision_uuid,
                    "nextRevisionId": snapshot_revision_uuid,
                }
            )
        return is_accepted

    def _get_spreadsheet_snapshot(self):
        snapshot_attachment = self.env['ir.attachment'].with_context(bin_size=False).search([
            ('res_model', '=', self._name),
            ('res_field', '=', 'spreadsheet_snapshot'),
            ('res_id', '=', self.id),
        ])
        if not snapshot_attachment and self.spreadsheet_data is False:
            return False
        elif not snapshot_attachment:
            return json.loads(self.spreadsheet_data or '{}')
        return json.loads(snapshot_attachment.raw or '{}')

    def _should_be_snapshotted(self):
        if not self.spreadsheet_revision_ids:
            return False
        last_activity = max(self.spreadsheet_revision_ids.mapped("create_date"))
        return last_activity < fields.Datetime.now() - timedelta(hours=2)

    def _save_concurrent_revision(self, next_revision_uuid, parent_revision_uuid, commands):
        """Save the given revision if no concurrency issue is found.
        i.e. if no other revision was saved based on the same `parent_revision_uuid`
        :param next_revision_uuid: the new revision id
        :param parent_revision_uuid: the revision on which the commands are based
        :param commands: revisions commands
        :return: True if the revision was saved, False otherwise
        """
        self.ensure_one()
        parent_revision_id = self._get_revision_by_uuid(parent_revision_uuid)
        try:
            with mute_logger("odoo.sql_db"):
                self.env["spreadsheet.revision"].create(
                    {
                        "res_model": self._name,
                        "res_id": self.id,
                        "commands": json.dumps(commands),
                        "parent_revision_id": parent_revision_id.id,
                        "revision_uuid": next_revision_uuid,
                        "create_date": fields.Datetime.now(),
                    }
                )
            return True
        except psycopg2.IntegrityError:
            # If the creation failed with a unique violation error, it is because the parent_revision_id has already
            # been used. This means that at the same (relative) time, another user has made a modification to the
            # document while this user also modified the document, without knowing about each other modification.
            # We don't need to do anything: when the client that already did the modification will be done, the
            # situation will resolve itself when this client receives the other client's modification.
            _logger.info("Wrong base spreadsheet revision on %s", self)
            return False

    def _build_spreadsheet_revision_data(self, message: CollaborationMessage) -> dict:
        """Prepare revision data to save in the database from
        the collaboration message.
        """
        message = dict(message)
        message.pop("serverRevisionId", None)
        message.pop("nextRevisionId", None)
        message.pop("clientId", None)
        return message

    def _build_spreadsheet_messages(self) -> List[CollaborationMessage]:
        """Build spreadsheet collaboration messages from the saved
        revision data"""
        self.ensure_one()
        return [
            dict(
                json.loads(rev.commands),
                serverRevisionId=rev.parent_revision_id.revision_uuid or self._get_initial_revision_uuid(),
                nextRevisionId=rev.revision_uuid,
            )
            for rev in self.spreadsheet_revision_ids
        ]

    def _check_collaborative_spreadsheet_access(
        self, operation: str, access_token=None, *, raise_exception=True
    ):
        """Check that the user has the right to read/write on the document.
        It's used to ensure that a user can read/write the spreadsheet revisions
        of this document.
        """
        try:
            self._check_spreadsheet_share(operation, access_token)
        except AccessError as e:
            if raise_exception:
                raise e
            return False
        return True

    def _check_spreadsheet_share(self, operation, access_token):
        """Delegates the sharing check to the underlying model which might
        implement sharing in different ways.
        """
        self.check_access(operation)

    def _broadcast_spreadsheet_message(self, message: CollaborationMessage):
        """Send the message to the spreadsheet channel"""
        self.ensure_one()
        self._bus_send("spreadsheet", dict(message, id=self.id))

    def _delete_collaborative_data(self):
        self.spreadsheet_snapshot = False
        self._check_collaborative_spreadsheet_access("write")
        self.with_context(active_test=False).sudo().spreadsheet_revision_ids.unlink()

    def unlink(self):
        """ Override unlink to delete spreadsheet revision. This cannot be
        cascaded, because link is done through (res_model, res_id). """
        if not self:
            return True
        self.sudo().with_context(active_test=False).spreadsheet_revision_ids.unlink()
        return super().unlink()

    def action_open_spreadsheet(self):
        raise NotImplementedError("This method is not implemented for model %s." % self._name)

    @api.model
    def action_open_new_spreadsheet(self, vals=None):
        spreadsheet = self.create(vals or {})
        return spreadsheet.action_open_spreadsheet()

    @api.model
    def get_selector_spreadsheet_models(self):
        selectable_models = []
        for model in self.env:
            if issubclass(self.pool[model], self.pool['spreadsheet.mixin']):
                selector = self.env[model]._get_spreadsheet_selector()
                if selector:
                    selectable_models.append(selector)
        selectable_models.sort(key=lambda m: m["sequence"])
        return selectable_models

    @api.model
    def _get_spreadsheet_selector(self):
        return None

    @api.model
    def _creation_msg(self):
        return self.env._("New spreadsheet created")

    @api.model
    def get_spreadsheets(self, domain=(), offset=0, limit=None):
        return {
            "total": self.search_count(domain),
            "records": self.search_read(domain, ["display_name", "thumbnail"], offset=offset, limit=limit)
        }

    def get_spreadsheet_history(self, from_snapshot=False):
        """Fetch the spreadsheet history.
         - if from_snapshot is provided, then provides the last snapshot and the revisions since then
         - otherwise, returns the empty skeleton of the spreadsheet with all the revisions since its creation
        """
        self.ensure_one()
        self._check_collaborative_spreadsheet_access("read")
        spreadsheet_sudo = self.sudo()
        initial_date = spreadsheet_sudo.create_date

        if from_snapshot:
            data = spreadsheet_sudo._get_spreadsheet_snapshot()
            revisions = spreadsheet_sudo.spreadsheet_revision_ids
            snapshot = spreadsheet_sudo.env["ir.attachment"].search([
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("res_field", "=", "spreadsheet_snapshot")
            ], order="write_date DESC", limit=1)
            initial_date = snapshot.write_date
        else:
            data = json.loads(self.spreadsheet_data)
            revisions = spreadsheet_sudo.with_context(active_test=False).spreadsheet_revision_ids

        return {
            "name": spreadsheet_sudo.display_name,
            "data": data,
            "revisions": [
                dict(
                    json.loads(rev.commands),
                    id=rev.id,
                    name=rev.name,
                    user=(rev.create_uid.id, rev.create_uid.name),
                    serverRevisionId=rev.parent_revision_id.revision_uuid or self._get_initial_revision_uuid(),
                    nextRevisionId=rev.revision_uuid,
                    timestamp=rev.create_date,
                )
                for rev in revisions
            ],
            "initial_date": initial_date,
            "default_currency": self.env["res.currency"].get_company_currency_for_spreadsheet(),
        }

    def rename_revision(self, revision_id, name):
        self.ensure_one()
        self._check_collaborative_spreadsheet_access("write")
        self.env["spreadsheet.revision"].sudo().browse(revision_id).name = name

    def fork_history(self, revision_id: int, spreadsheet_snapshot: dict, default: Optional[dict] = None):
        self.ensure_one()
        default = default or {}
        default['spreadsheet_revision_ids'] = []
        default['spreadsheet_data'] = self.spreadsheet_data
        new_spreadsheet = self.copy(default)
        self.with_context(active_test=False)._copy_revisions_to(new_spreadsheet, revision_id)
        new_spreadsheet.spreadsheet_snapshot = base64.b64encode(json.dumps(spreadsheet_snapshot).encode())
        new_spreadsheet.spreadsheet_revision_ids.active = False
        new_spreadsheet._delete_comments_from_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'message': self._creation_msg(),
                'next': new_spreadsheet.action_open_spreadsheet(),
            }
        }

    def restore_spreadsheet_version(self, revision_id: int, spreadsheet_snapshot: dict):
        self.ensure_one()
        self._check_collaborative_spreadsheet_access("write")
        
        spreadsheet = self.sudo()
        all_revisions = spreadsheet.with_context(active_test=False).spreadsheet_revision_ids
        revisions_after = all_revisions.filtered(lambda r: r.id > revision_id)
        revisions_after.unlink()

        current_revision_uuid = spreadsheet.env["spreadsheet.revision"].browse(revision_id).revision_uuid
        snapshot_revision_uuid = str(uuid.uuid4())
        spreadsheet_snapshot["revisionId"] = snapshot_revision_uuid
        # other collaborative users will receive the snapshot message based on
        # a server revision id they do not expect. This will cause them to reload.
        is_accepted = spreadsheet._snapshot_spreadsheet(
            current_revision_uuid,
            snapshot_revision_uuid,
            spreadsheet_snapshot,
        )
        if not is_accepted:
            raise UserError(_("The operation could not be applied because of a concurrent update. Please try again."))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'message': _("Version restored"),
                'next': self.action_open_spreadsheet(),
            }
        }

    def _get_context_company_colors(self):
        companies = self.env.companies
        colors = OrderedSet()
        for company in companies:
            colors.add(company.primary_color)
            colors.add(company.secondary_color)
            colors.add(company.email_primary_color)
            colors.add(company.email_secondary_color)
        colors.discard(False)
        return list(colors)

    def _dispatch_command(self, command):
        self._dispatch_commands([command])

    def _dispatch_commands(self, commands):
        is_accepted = self.dispatch_spreadsheet_message(self._build_new_revision_data(commands))
        if not is_accepted:
            raise UserError(_("The operation could not be applied because of a concurrent update. Please try again."))

    def _build_new_revision_data(self, commands):
        return {
            "type": "REMOTE_REVISION",
            "serverRevisionId": self.current_revision_uuid,
            "nextRevisionId": str(uuid.uuid4()),
            "commands": commands,
        }

    def _get_revision_by_uuid(self, revision_uuid):
        return (
            self.env["spreadsheet.revision"]
            .with_context(active_test=False)
            .search(
                [
                    ("revision_uuid", "=", revision_uuid),
                    ("res_id", "=", self.id),
                    ("res_model", "=", self._name),
                ],
                limit=1,
            )
        )

    def _get_initial_revision_uuid(self):
        data = json.loads(self.spreadsheet_data)
        return data.get("revisionId", "START_REVISION")

    def _delete_comments_from_data(self):
        """ Deletes comments data from the spreadsheet data and its snapshot """
        self = self.with_context(preserve_spreadsheet_revisions=True)
        for spreadsheet in self:
            if spreadsheet.spreadsheet_data:
                spreadsheet_data = json.loads(spreadsheet.spreadsheet_data)
                sheets = spreadsheet_data.get('sheets', [])
                for sheet in sheets:
                    sheet['comments'] = {}
                spreadsheet.spreadsheet_data = json.dumps(spreadsheet_data)
            if spreadsheet.spreadsheet_snapshot:
                spreadsheet_snapshot = json.loads(base64.decodebytes(spreadsheet.spreadsheet_snapshot))
                if 'sheets' in spreadsheet_snapshot:
                    for sheet in spreadsheet_snapshot['sheets']:
                        if "comments" in sheet:
                            sheet['comments'] = {}
                    spreadsheet.spreadsheet_snapshot = base64.b64encode(
                        json.dumps(spreadsheet_snapshot).encode()
                    )

    def _delete_comments_from_commands(self, revision_commands_string):
        """ Deletes comments related from the commands """
        revision_commands = json.loads(revision_commands_string)
        if not isinstance(revision_commands, dict):
            return revision_commands_string

        commands = revision_commands.get('commands', [])
        if not len(commands) > 0:
            return revision_commands_string
        for index, command in enumerate(commands):
            if command['type'] in ("ADD_COMMENT_THREAD", "DELETE_COMMENT_THREAD", "EDIT_COMMENT_THREAD"):
                commands.pop(index)
        revision_commands['commands'] = commands
        return json.dumps(revision_commands)

    def _copy_spreadsheet_image_attachments(self):
        """Ensures the image attachments are linked to the spreadsheet record
        and duplicates them if necessary and updates the spreadsheet data and revisions to
        point to the new attachments."""
        self._check_collaborative_spreadsheet_access("write")
        for spreadsheet in self:
            revisions = spreadsheet.sudo().with_context(active_test=False).spreadsheet_revision_ids
            mapping = {}  # old_attachment_id: new_attachment
            revisions_with_images = revisions.filtered(lambda r: "CREATE_IMAGE" in r.commands)
            for revision in revisions_with_images:
                data = json.loads(revision.commands)
                commands = data.get("commands", [])
                for command in commands:
                    if command["type"] == "CREATE_IMAGE" and command["definition"]["path"].startswith("/web/image/"):
                        attachment_copy = spreadsheet._get_spreadsheet_image_attachment(command["definition"]["path"], mapping)
                        if attachment_copy:
                            command["definition"]["path"] = get_attachment_image_src(command["definition"]["path"], attachment_copy)
                revision.commands = json.dumps(data)
            data = json.loads(spreadsheet.spreadsheet_data) if spreadsheet.spreadsheet_data else {}
            spreadsheet._copy_spreadsheet_images_data(data, mapping)
            if spreadsheet.spreadsheet_snapshot:
                snapshot = spreadsheet._get_spreadsheet_snapshot()
                spreadsheet._copy_spreadsheet_images_data(snapshot, mapping)
            if mapping:
                spreadsheet.with_context(preserve_spreadsheet_revisions=True).spreadsheet_data = json.dumps(data)
                if spreadsheet.spreadsheet_snapshot:
                    spreadsheet.spreadsheet_snapshot = base64.encodebytes(json.dumps(snapshot).encode())

    def _copy_spreadsheet_images_data(self, data, mapping):
        for sheet in data.get("sheets", []):
            for figure in sheet.get("figures", []):
                if figure["tag"] == "image" and figure["data"]["path"].startswith("/web/image/"):
                    attachment_copy = self._get_spreadsheet_image_attachment(figure["data"]["path"], mapping)
                    if attachment_copy:
                        figure["data"]["path"] = get_attachment_image_src(figure["data"]["path"], attachment_copy)

    def _get_spreadsheet_image_attachment(self, path: str, mapping):
        attachment_id = int(path.split("/")[3].split("?")[0])
        attachment = self.env["ir.attachment"].browse(attachment_id).exists()
        if attachment and (attachment.res_model != self._name or attachment.res_id != self.id):
            attachment_copy = mapping.get(attachment_id) or attachment.copy({"res_model": self._name, "res_id": self.id})
            mapping[attachment_id] = attachment_copy
            return attachment_copy
        return self.env["ir.attachment"]
    
    def _inverse_display_thumbnail(self):
        for spreadsheet in self:
            value = base64.b64encode(image_process(base64.b64decode(self.display_thumbnail or ''), (150, 150), crop='center'))
            thumbnail = self.sudo().env["ir.attachment"].search([
                ("res_model", "=", self._name),
                ("res_id", "=", spreadsheet.id),
                ("create_uid", "=", self.env.uid),
                ("res_field", "=", "display_thumbnail"),
            ], limit=1)
            if thumbnail:
                thumbnail.datas = value
            else:
                self.env["ir.attachment"].create({
                    "res_model": self._name,
                    "res_id": spreadsheet.id,
                    "res_field": "display_thumbnail",
                    "datas": value,
                    "name": f"{self._name},{spreadsheet.id},{self.env.uid}"
                })

    @api.depends_context('uid')
    @api.depends('thumbnail')
    def _compute_display_thumbnail(self):
        # Spreadsheet thumbnails cannot be computed from their binary data.
        # They should be saved independently.
        spreadsheets = self.filtered(lambda d: (d.handler if "handler" in d._fields else 'spreadsheet') == 'spreadsheet')
        thumbnails = spreadsheets.sudo().env["ir.attachment"].search([
            ("res_model", "=", self._name),
            ("res_id", "in", spreadsheets.ids),
            ("res_field", "=", "display_thumbnail"),
            ("create_uid", "=", spreadsheets.env.uid),
        ])
        thumbnails = {self.browse(tn.res_id): tn.datas for tn in thumbnails}
        for spreadsheet in spreadsheets:
            spreadsheet.display_thumbnail = thumbnails.get(spreadsheet, False)

    def _get_writable_record_name_field(self):
        if self._rec_name and not self._fields[self._rec_name].readonly:
            return self._fields[self._rec_name].name
        return None


def get_attachment_image_src(original_path, attachment_copy):
    has_access_token = f"access_token={attachment_copy.access_token}" in original_path
    if has_access_token:
        return f"/web/image/{attachment_copy.id}?access_token={attachment_copy.access_token}"
    return f"/web/image/{attachment_copy.id}"
