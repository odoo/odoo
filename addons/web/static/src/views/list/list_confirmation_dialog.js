import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useAutofocus } from "@web/core/utils/hooks";
import { Operation } from "@web/model/relational_model/operation";
import { Field, fieldVisualFeedback } from "@web/views/fields/field";

import { Component } from "@odoo/owl";

export class ListConfirmationDialog extends Component {
    static template = "web.ListView.ConfirmationModal";
    static components = { Dialog, Field };
    static props = {
        close: Function,
        title: {
            validate: (m) =>
                typeof m === "string" ||
                (typeof m === "object" && typeof m.toString === "function"),
            optional: true,
        },
        confirm: { type: Function, optional: true },
        cancel: { type: Function, optional: true },
        isDomainSelected: Boolean,
        fields: Object,
        nbRecords: Number,
        nbValidRecords: Number,
        record: Object,
        changes: Object,
    };
    static defaultProps = {
        title: _t("Confirmation"),
    };

    setup() {
        useAutofocus();
    }

    get validRecordsText() {
        return _t(
            "Among the %(total)s selected records, %(valid_count)s are valid for this update.",
            {
                total: this.props.nbRecords,
                valid_count: this.props.nbValidRecords,
            }
        );
    }

    get updateConfirmationText() {
        return _t("Are you sure you want to update %(count)s records?", {
            count: this.props.nbValidRecords,
        });
    }

    get showTip() {
        return this.props.fields.some((field) =>
            ["monetary", "integer", "float"].includes(field.fieldNode?.type)
        );
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

    /**
     * Whether the Field component would show nothing
     */
    isValueEmpty(field) {
        // force readonly as we force that state on the Field component
        return fieldVisualFeedback(field, this.props.record, field.name, {
            ...field.fieldNode,
            readonly: true,
        }).empty;
    }

    isValueOperation(field) {
        return this.props.changes[field.name] instanceof Operation;
    }
}
