import { Component, t, useProps } from "@odoo/owl";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { ImportDataColumnError } from "../import_data_column_error/import_data_column_error";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

export class ImportDataContent extends Component {
    static template = "ImportDataContent";
    static components = {
        ImportDataColumnError,
        SelectMenu,
    };

    props = useProps({
        columns: t.array(),
        importMessages: t.array(t.object()),
        isFieldSet: t.function(),
        languagesInstalled: t.array(),
        onErrorResolved: t.function(),
        onFieldChanged: t.function(),
        onFieldLanguageChanged: t.function(),
        options: t.object(),
        previewError: t.string().optional(),
        resultNames: t.array(),
    });

    setup() {
        this.hasMultipleLanguages = this.props.languagesInstalled.length > 1;
        this.userLanguage = user.lang.replace("-", "_");
    }

    get hasErrors() {
        return this.props.columns.some((column) => column.errors.length);
    }

    getGroups(column) {
        const groups = [
            { choices: this.makeChoices(column.fields.basic) },
            { choices: this.makeChoices(column.fields.required), label: _t("Required Fields") },
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
            iconClass: `o_import_field_icon_${field.type}`,
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
        const isLast = index === column.comments.length - 1 && !column.errors.length;
        return `alert-${comment.type} ${isLast ? "mb-0" : "mb-2"}`;
    }

    onFieldChanged(column, fieldPath) {
        const fields = [
            ...column.fields.basic,
            ...column.fields.required,
            ...column.fields.suggested,
            ...column.fields.additional,
            ...column.fields.relational,
        ];
        const fieldInfo = fields.find((f) => f.fieldPath === fieldPath);
        this.props.onFieldChanged(column, fieldInfo);
    }

    getLanguages() {
        return this.props.languagesInstalled.map((val) => ({
            value: val[0],
            label: val[1],
        }));
    }

    getLanguagesLabel(value) {
        return this.props.languagesInstalled.find((val) => val[0] === value)?.[1];
    }

    setLanguage(column, language) {
        this.props.onFieldLanguageChanged(column, language);
    }
}
