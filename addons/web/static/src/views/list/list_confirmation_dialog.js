import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useAutofocus } from "@web/core/utils/hooks";
import { TagsList } from "@web/core/tags_list/tags_list";
import { Operation } from "@web/model/relational_model/operation";
import { Field, fieldVisualFeedback } from "@web/views/fields/field";

import { Component } from "@odoo/owl";

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
        selection: Array,
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
                total: this.props.selection.length,
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

    getTagProps(record) {
        return {
            id: record.id, // datapoint_X
            resId: record.resId,
            text: record.data.display_name,
            colorIndex: record.data[this.props.colorField],
        };
    }

    getChanges(field) {
        const selectionChangeIds = this.props.selection.map((record) => {
            const changes = record._changes[field.name];
            if (!changes) {
                return [];
            }
            const initialCurrentIds = changes._initialCurrentIds;
            const currentIds = changes._currentIds;
            return [
                ...currentIds.filter((id) => !initialCurrentIds.includes(id)),
                ...initialCurrentIds.filter((id) => !currentIds.includes(id)).map((id) => -id),
            ];
        });
        const uniqueIds = [...new Set(selectionChangeIds.flat())];
        return {
            operation: uniqueIds[0] < 0 ? _t("Remove") : _t("Add"),
            tags: uniqueIds.map((_id) => {
                const id = Math.abs(_id);
                const record = this.props.changes[field.name]._cache[id];
                return this.getTagProps(record);
            }),
        };
    }

    isManyToManyField(field) {
        const fieldNode = field.fieldNode || {};
        return ["many2many"].includes(fieldNode.type);
    }

    isValueEmpty(field) {
        const fieldNode = field.fieldNode || {};
        return fieldVisualFeedback(fieldNode.field || {}, this.props.record, field.name, {
            ...fieldNode,
            // force readonly as we force that state on the Field component
            readonly: true,
        }).empty;
    }

    isValueOperation(field) {
        return this.props.changes[field.name] instanceof Operation;
    }
}
