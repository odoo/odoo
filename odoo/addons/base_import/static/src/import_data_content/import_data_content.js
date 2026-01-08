/** @odoo-module **/

import { Component } from "@odoo/owl";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { ImportDataColumnError } from "../import_data_column_error/import_data_column_error";
import { ImportDataOptions } from "../import_data_options/import_data_options";
import { _t } from "@web/core/l10n/translation";

export class ImportDataContent extends Component {
    static template = "ImportDataContent";
    static components = {
        ImportDataColumnError,
        ImportDataOptions,
        SelectMenu,
    };
    static props = {
        columns: { type: Array },
        isFieldSet: { type: Function },
        onOptionChanged: { type: Function },
        onFieldChanged: { type: Function },
        options: { type: Object },
        importMessages: { type: Object },
        previewError: { type: String, optional: true },
    };

    setup() {
        this.searchPlaceholder = _t("Search a field...");
    }

    getGroups(column) {
        const groups = [
            { choices: this.makeChoices(column.fields.basic) },
            { choices: this.makeChoices(column.fields.suggested), label: _t("Suggested Fields") },
            {
                choices: this.makeChoices(column.fields.additional),
                label:
                    column.fields.suggested.length > 0
                        ? _t("Additional Fields")
                        : _t("Standard Fields"),
            },
            { choices: this.makeChoices(column.fields.relational), label: _t("Relation Fields") },
        ];
        return groups;
    }

    makeChoices(fields) {
        return fields.map((field) => ({
            label: field.label,
            value: field.fieldPath,
        }));
    }

    getTooltipDetails(field) {
        return JSON.stringify({
            resModel: field.model_name,
            debug: true,
            field: {
                name: field.name,
                label: field.string,
                type: field.type,
            },
        });
    }

    getTooltip(column) {
        const displayCount = 5;
        if (column.previews.length > displayCount) {
            return JSON.stringify({
                lines: [
                    ...column.previews.slice(0, displayCount - 1),
                    `(+${column.previews.length - displayCount + 1})`,
                ],
            });
        } else {
            return JSON.stringify({ lines: column.previews.slice(0, displayCount) });
        }
    }

    getErrorMessageClass(messages, type, index) {
        return `alert alert-${type} m-0 p-2 ${index === messages.length - 1 ? "" : "mb-2"}`;
    }

    getCommentClass(column, comment, index) {
        return `alert-${comment.type} ${index < column.comments.length - 1 ? "mb-2" : "mb-0"}`;
    }

    onFieldChanged(column, fieldPath) {
        const fields = [
            ...column.fields.basic,
            ...column.fields.suggested,
            ...column.fields.additional,
            ...column.fields.relational,
        ];
        const fieldInfo = fields.find((f) => f.fieldPath === fieldPath);
        this.props.onFieldChanged(column, fieldInfo);
    }
}
