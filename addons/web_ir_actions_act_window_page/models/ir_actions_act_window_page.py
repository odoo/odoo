# Copyright 2023 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class IrActionsActWindowPagePrev(models.AbstractModel):
    _name = "ir.actions.act_window.page.prev"
    _description = "Action to page to the previous record from a form view button"

    def _get_readable_fields(self):
        return set()  # pragma: no cover


class IrActionsActWindowPageNext(models.AbstractModel):
    _name = "ir.actions.act_window.page.next"
    _description = "Action to page to the next record from a form view button"

    def _get_readable_fields(self):
        return set()  # pragma: no cover


class IrActionsActWindowPageList(models.AbstractModel):
    _name = "ir.actions.act_window.page.list"
    _description = "Action to switch to the list view"

    def _get_readable_fields(self):
        return set()  # pragma: no cover
