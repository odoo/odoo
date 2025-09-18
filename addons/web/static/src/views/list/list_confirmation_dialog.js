// @ts-check

/** @module @web/views/list/list_confirmation_dialog - Confirmation dialog for multi-record bulk edits showing affected records and changed values */

import { Component } from "@odoo/owl";
import { TagsList } from "@web/components/tags_list/tags_list";
import { _t } from "@web/core/l10n/translation";
import { useAutofocus } from "@web/core/utils/hooks";
import { Field, fieldVisualFeedback } from "@web/fields/field";
import { Operation } from "@web/model/relational_model/operation";
import { Dialog } from "@web/ui/dialog/dialog";

/**
 * Confirmation dialog shown before applying multi-record edits.
 *
 * Displays the number of affected records, the fields being changed, and
 * their new values. Lets the user confirm or cancel the bulk update.
 */
export class ListConfirmationDialog extends Component {
    static template = "web.ListView.ConfirmationModal";
    static components = { Dialog, Field, TagsList };
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

    /** @returns {string} Translated text indicating how many selected records are valid. */
    get validRecordsText() {
        return _t(
            "Among the %(total)s selected records, %(valid_count)s are valid for this update.",
            {
                total: this.props.nbRecords,
                valid_count: this.props.nbValidRecords,
            },
        );
    }

    /** @returns {string} Translated confirmation prompt with the record count. */
    get updateConfirmationText() {
        return _t("Are you sure you want to update %(count)s records?", {
            count: this.props.nbValidRecords,
        });
    }

    /** @returns {boolean} Whether to show a tip about numeric field operations. */
    get showTip() {
        return this.props.fields.some((field) =>
            ["monetary", "integer", "float"].includes(field.fieldNode?.type),
        );
    }

    /** Invoke the cancel callback (if provided) and close the dialog. */
    _cancel() {
        if (this.props.cancel) {
            this.props.cancel();
        }
        this.props.close();
    }

    /** Invoke the confirm callback (if provided) and close the dialog. */
    async _confirm() {
        if (this.props.confirm) {
            await this.props.confirm();
        }
        this.props.close();
    }

    /**
     * Build tag props for a many2many field displayed as a TagsList.
     *
     * @param {any[]} records - related records for the field
     * @param {{ fieldNode: any }} field - field descriptor with its arch node
     * @returns {{ id: any, resId: any, text: string, colorIndex: any }[]}
     */
    getTagProps(records, field) {
        const colorField = field.fieldNode.options?.color_field;
        return records.map((record) => ({
            id: record.id,
            resId: record.resId,
            text: record.data.display_name,
            colorIndex: colorField ? record.data[colorField] : undefined,
        }));
    }

    /**
     * Check whether the field's current value should display as empty.
     *
     * @param {{ fieldNode: any, name: string }} field
     * @returns {boolean}
     */
    isValueEmpty(field) {
        const fieldNode = field.fieldNode || {};
        return fieldVisualFeedback(
            fieldNode.field || {},
            this.props.record,
            field.name,
            {
                ...fieldNode,
                // force readonly as we force that state on the Field component
                readonly: true,
            },
        ).empty;
    }

    /**
     * Check whether the change for this field is an Operation (e.g. increment).
     *
     * @param {{ name: string }} field
     * @returns {boolean}
     */
    isValueOperation(field) {
        return this.props.changes[field.name] instanceof Operation;
    }
}
