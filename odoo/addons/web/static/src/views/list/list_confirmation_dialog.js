/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { Field } from "@web/views/fields/field";
import { useAutofocus } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

export class ListConfirmationDialog extends Component {
    setup() {
        useAutofocus();
    }

    _cancel() {
        if (this.props.cancel) {
            this.props.cancel();
        }
        this.props.close();
    }

    async _confirm() {
        if (this.props.confirm) {
            await this.props.confirm();
        }
        this.props.close();
    }
}
ListConfirmationDialog.template = "web.ListView.ConfirmationModal";
ListConfirmationDialog.components = { Dialog, Field };
ListConfirmationDialog.props = {
    close: Function,
    title: {
        validate: (m) => {
            return (
                typeof m === "string" || (typeof m === "object" && typeof m.toString === "function")
            );
        },
        optional: true,
    },
    confirm: { type: Function, optional: true },
    cancel: { type: Function, optional: true },
    isDomainSelected: Boolean,
    fields: Object,
    nbRecords: Number,
    nbValidRecords: Number,
    record: Object,
};
ListConfirmationDialog.defaultProps = {
    title: _t("Confirmation"),
};
