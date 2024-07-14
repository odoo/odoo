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
from odoo.tools import mute_logger
_logger = logging.getLogger(__name__)

CollaborationMessage = Dict[str, Any]


class SpreadsheetMixin(models.AbstractModel):
    _inherit = "spreadsheet.mixin"

    spreadsheet_snapshot = fields.Binary()
    spreadsheet_revision_ids = fields.One2many(
        "spreadsheet.revision",
        "res_id",
        domain=lambda self: [('res_model', '=', self._name)],
        groups="base.group_system",
    )
    # The last revision id known by the current transaction.
    # Another concurrent transaction can have saved a revision after this one
    # This means it cannot be blindly used to dispatch a new revision.
    server_revision_id = fields.Char(compute="_compute_server_revision_id", compute_sudo=True)

    @api.depends("spreadsheet_revision_ids", "spreadsheet_snapshot", "spreadsheet_data")
    def _compute_server_revision_id(self):
        for spreadsheet in self:
            revisions = spreadsheet.spreadsheet_revision_ids
            if revisions:
                spreadsheet.server_revision_id = revisions[-1].revision_id
            else:
                snapshot = spreadsheet._get_spreadsheet_snapshot()
                if snapshot is False:
                    spreadsheet.server_revision_id = False
                else:
                    spreadsheet.server_revision_id = snapshot.get("revisionId", "START_REVISION")

    def write(self, vals):
        if "spreadsheet_binary_data" in vals and not self.env.context.get("preserve_spreadsheet_revisions"):
            self._delete_collaborative_data()
        return super().write(vals)

    def copy(self, default=None):
        default = default or {}
        self.ensure_one()
        if "spreadsheet_data" not in default:
            default["spreadsheet_data"] = self.spreadsheet_data
        self = self.with_context(preserve_spreadsheet_revisions=True)
        new_spreadsheet = super().copy(default)
        if not default or "spreadsheet_revision_ids" not in default:
            self._copy_revisions_to(new_spreadsheet)
        new_spreadsheet._copy_spreadsheet_image_attachments()
        return new_spreadsheet

    @api.model_create_multi
    def create(self, vals_list):
        spreadsheets = super().create(vals_list)
        for spreadsheet in spreadsheets:
            spreadsheet._copy_spreadsheet_image_attachments()
        return spreadsheets

    def join_spreadsheet_session(self, share_id=None, access_token=None):
        """Join a spreadsheet session.
        Returns the following data::
        - the last snapshot
        - pending revisions since the last snapshot
        - the spreadsheet name
        - whether the user favorited the spreadsheet or not
        - whether the user can edit the content of the spreadsheet or not
        """
        self.ensure_one()
        self._check_collaborative_spreadsheet_access("read", share_id, access_token)
        can_write = self._check_collaborative_spreadsheet_access(
            "write", share_id, access_token, raise_exception=False
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
            "user_locale": self.env["res.lang"]._get_user_spreadsheet_locale()
        }

    def dispatch_spreadsheet_message(self, message: CollaborationMessage, share_id=None, access_token=None):
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
            self._check_collaborative_spreadsheet_access("write", share_id, access_token)
            is_accepted = self.sudo()._save_concurrent_revision(
                message["nextRevisionId"],
                message["serverRevisionId"],
                self._build_spreadsheet_revision_data(message),
            )
            if is_accepted:
                self._broadcast_spreadsheet_message(message)
            return is_accepted
        elif message["type"] == "SNAPSHOT":
            self._check_collaborative_spreadsheet_access("write", share_id, access_token)
            return self.sudo()._snapshot_spreadsheet(
                message["serverRevisionId"], message["nextRevisionId"], message["data"]
            )
        elif message["type"] in ["CLIENT_JOINED", "CLIENT_LEFT", "CLIENT_MOVED"]:
            self._check_collaborative_spreadsheet_access("read", share_id, access_token)
            self._broadcast_spreadsheet_message(message)
            return True
        return False

    def _copy_revisions_to(self, spreadsheet, up_to_revision_id=False):
        self._check_collaborative_spreadsheet_access("read")
        revisions_data = []
        if up_to_revision_id:
            revisions = self.sudo().spreadsheet_revision_ids.filtered(
                lambda r: r.id <= up_to_revision_id
            )
        else:
            revisions = self.sudo().spreadsheet_revision_ids
        for revision in revisions:
            revisions_data += revision.copy_data({
                "res_model": spreadsheet._name,
                "res_id": spreadsheet.id,
            })
        spreadsheet._check_collaborative_spreadsheet_access("write")
        revisions = self.env["spreadsheet.revision"].sudo().create(revisions_data)
        spreadsheet.sudo().spreadsheet_revision_ids = revisions

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
        self, revision_id: str, snapshot_revision_id, spreadsheet_snapshot: dict
    ):
        """Save the spreadsheet snapshot along the revision id. Delete previous
        revisions which are no longer needed.
        If the `revision_id` is not the same as the server revision, the snapshot is
        not accepted and is ignored.

        :param revision_id: the revision on which the snapshot is based
        :param snapshot_revision_id: snapshot revision
        :param spreadsheet_snapshot: spreadsheet data
        :return: True if the snapshot was saved, False otherwise
        """
        if snapshot_revision_id != spreadsheet_snapshot.get("revisionId"):
            raise ValueError("The snapshot revision id does not match the revision id")

        is_accepted = self._save_concurrent_revision(
            snapshot_revision_id,
            revision_id,
            {"type": "SNAPSHOT_CREATED", "version": 1},
        )
        if is_accepted:
            self.spreadsheet_snapshot = base64.b64encode(
                json.dumps(spreadsheet_snapshot).encode("utf-8")
            )
            self.spreadsheet_revision_ids.active = False
            self._broadcast_spreadsheet_message(
                {
                    "type": "SNAPSHOT_CREATED",
                    "serverRevisionId": revision_id,
                    "nextRevisionId": snapshot_revision_id,
                }
            )
        return is_accepted

    def _get_spreadsheet_snapshot(self):
        if self.spreadsheet_snapshot is False and self.spreadsheet_data is False:
            return False
        elif self.spreadsheet_snapshot is False:
            return json.loads(self.spreadsheet_data)
        return json.loads(base64.decodebytes(self.spreadsheet_snapshot))

    def _should_be_snapshotted(self):
        if not self.spreadsheet_revision_ids:
            return False
        last_activity = max(self.spreadsheet_revision_ids.mapped("create_date"))
        return last_activity < fields.Datetime.now() - timedelta(hours=2)

    def _save_concurrent_revision(self, next_revision_id, parent_revision_id, commands):
        """Save the given revision if no concurrency issue is found.
        i.e. if no other revision was saved based on the same `parent_revision_id`
        :param next_revision_id: the new revision id
        :param parent_revision_id: the revision on which the commands are based
        :param commands: revisions commands
        :return: True if the revision was saved, False otherwise
        """
        self.ensure_one()
        try:
            with mute_logger("odoo.sql_db"):
                self.env["spreadsheet.revision"].create(
                    {
                        "res_model": self._name,
                        "res_id": self.id,
                        "commands": json.dumps(commands),
                        "parent_revision_id": parent_revision_id,
                        "revision_id": next_revision_id,
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
                serverRevisionId=rev.parent_revision_id,
                nextRevisionId=rev.revision_id,
            )
            for rev in self.spreadsheet_revision_ids
        ]

    def _check_collaborative_spreadsheet_access(
        self, operation: str, share_id=None, access_token=None, *, raise_exception=True
    ):
        """Check that the user has the right to read/write on the document.
        It's used to ensure that a user can read/write the spreadsheet revisions
        of this document.
        """
        try:
            if share_id and access_token:
                self._check_spreadsheet_share(operation, share_id, access_token)
            else:
                self.check_access_rights(operation)
                self.check_access_rule(operation)
        except AccessError as e:
            if raise_exception:
                raise e
            return False
        return True

    def _check_spreadsheet_share(self, operation, share_id, access_token):
        """Delegates the sharing check to the underlying model which might
        implement sharing in different ways.
        """
        raise AccessError(_("You are not allowed to access this spreadsheet."))

    def _broadcast_spreadsheet_message(self, message: CollaborationMessage):
        """Send the message to the spreadsheet channel"""
        self.ensure_one()
        self.env["bus.bus"]._sendone(self, "spreadsheet", dict(message, id=self.id))

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

    def action_edit(self):
        raise NotImplementedError("This method is not implemented in class %s." % self._name)

    @api.model
    def _creation_msg(self):
        raise NotImplementedError("This method is not implemented in class %s." % self._name)

    def get_spreadsheet_history(self, from_snapshot=False):
        """Fetch the spreadsheet history.
         - if from_snapshot is provided, then provides the last snapshot and the revisions since then
         - otherwise, returns the empty skeleton of the spreadsheet with all the revisions since its creation
        """
        self.ensure_one()
        self._check_collaborative_spreadsheet_access("read")
        spreadsheet_sudo = self.sudo()

        if from_snapshot:
            data = spreadsheet_sudo._get_spreadsheet_snapshot()
            revisions = spreadsheet_sudo.spreadsheet_revision_ids
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
                    serverRevisionId=rev.parent_revision_id,
                    nextRevisionId=rev.revision_id,
                    timestamp=rev.create_date,
                )
                for rev in revisions
            ],
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
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'message': self._creation_msg(),
                'next': new_spreadsheet.action_edit(),
            }
        }

    def _dispatch_command(self, command):
        is_accepted = self.dispatch_spreadsheet_message(self._build_new_revision_data(command))
        if not is_accepted:
            raise UserError(_("The operation could not be applied because of a concurrent update. Please try again."))

    def _build_new_revision_data(self, command):
        return {
            "type": "REMOTE_REVISION",
            "serverRevisionId": self.server_revision_id,
            "nextRevisionId": str(uuid.uuid4()),
            "commands": [command],
        }

    def _copy_spreadsheet_image_attachments(self):
        """Ensures the image attachments are linked to the spreadsheet record
        and duplicates them if necessary and updates the spreadsheet data and revisions to
        point to the new attachments."""
        self._check_collaborative_spreadsheet_access("write")
        revisions = self.sudo().with_context(active_test=False).spreadsheet_revision_ids
        mapping = {}  # old_attachment_id: new_attachment
        revisions_with_images = revisions.filtered(lambda r: "CREATE_IMAGE" in r.commands)
        for revision in revisions_with_images:
            data = json.loads(revision.commands)
            commands = data.get("commands", [])
            for command in commands:
                if command["type"] == "CREATE_IMAGE" and command["definition"]["path"].startswith("/web/image/"):
                    attachment_copy = self._get_spreadsheet_image_attachment(command["definition"]["path"], mapping)
                    if attachment_copy:
                        command["definition"]["path"] = f"/web/image/{attachment_copy.id}"
            revision.commands = json.dumps(data)
        data = json.loads(self.spreadsheet_data)
        self._copy_spreadsheet_images_data(data, mapping)
        if self.spreadsheet_snapshot:
            snapshot = self._get_spreadsheet_snapshot()
            self._copy_spreadsheet_images_data(snapshot, mapping)
        if mapping:
            self.with_context(preserve_spreadsheet_revisions=True).spreadsheet_data = json.dumps(data)
            if self.spreadsheet_snapshot:
                self.spreadsheet_snapshot = base64.encodebytes(json.dumps(snapshot).encode())

    def _copy_spreadsheet_images_data(self, data, mapping):
        for sheet in data.get("sheets", []):
            for figure in sheet.get("figures", []):
                if figure["tag"] == "image" and figure["data"]["path"].startswith("/web/image/"):
                    attachment_copy = self._get_spreadsheet_image_attachment(figure["data"]["path"], mapping)
                    if attachment_copy:
                        figure["data"]["path"] = f"/web/image/{attachment_copy.id}"

    def _get_spreadsheet_image_attachment(self, path: str, mapping):
        attachment_id = int(path.split("/")[3].split("?")[0])
        attachment = self.env["ir.attachment"].browse(attachment_id).exists()
        if attachment and (attachment.res_model != self._name or attachment.res_id != self.id):
            attachment_copy = mapping.get(attachment_id) or attachment.copy({"res_model": self._name, "res_id": self.id})
            mapping[attachment_id] = attachment_copy
            return attachment_copy
        return self.env["ir.attachment"]
