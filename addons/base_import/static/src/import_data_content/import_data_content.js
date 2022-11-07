/** @odoo-module **/

import { Component } from "@odoo/owl";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { ImportDataColumnError } from "../import_data_column_error/import_data_column_error";
import { ImportDataOptions } from "../import_data_options/import_data_options";
import { _t } from "@web/core/l10n/translation";

export class ImportDataContent extends Component {
    getOptions(column) {
        const options = this.makeOptions(column.fields.basic);

        function addOptions(fields, label) {
            const fieldOptions = this.makeOptions(fields);
            if (fieldOptions.length > 0) {
                options.push({ label: _t(label), isGroup: true }, ...fieldOptions);
            }
        }

        addOptions.bind(this)(column.fields.suggested, "Suggested Field");
        addOptions.bind(this)(column.fields.additional, "Additional Field");
        addOptions.bind(this)(column.fields.relational, "Relation Field");

        return options;
    }

    makeOptions(fields) {
        return fields.map((field) => ({
            label: field.string,
            value: field,
            template: "ImportDataContent.dropdownOptionTemplate",
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
}

ImportDataContent.template = "ImportDataContent";
ImportDataContent.components = {
    ImportDataColumnError,
    ImportDataOptions,
    SelectMenu,
};

ImportDataContent.props = {
    columns: { type: Array },
    isFieldSet: { type: Function },
    onOptionChanged: { type: Function },
    onFieldChanged: { type: Function },
    options: { type: Object },
    importMessages: { type: Object },
    previewError: { type: String, optional: true },
};
