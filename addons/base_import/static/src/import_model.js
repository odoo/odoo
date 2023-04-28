/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { groupBy, sortBy } from "@web/core/utils/arrays";
import { sprintf } from "@web/core/utils/strings";
import { useState } from "@odoo/owl";
import { ImportBlockUI } from "./import_block_ui";
import { moment_to_strftime_format } from "web.time";

const mainComponentRegistry = registry.category("main_components");

/**
 * -------------------------------------------------------------------------
 * Base Import Business Logic
 * -------------------------------------------------------------------------
 *
 * Handles mapping and updating the preview data of the csv/excel files to be
 * used in the different base_import components.
 *
 * When uploading a file some "preview data" is returned by the backend, this
 * data consist of the different columns of the file and the odoo fields which
 * these columns can be mapped to.
 *
 * Only a small selection of the lines are returned so the user can get an idea
 * of how to correctly map the columns. *(this is why it is refered as "preview
 * data")*
 *
 */
export class BaseImportModel {
    constructor({ env, resModel, context, orm }) {
        this.id = 1;
        this.env = env;
        this.orm = orm;
        this.handleInterruption = false;

        this.resModel = resModel;
        this.context = context || {};

        this.fields = [];
        this.columns = [];
        this.importMessages = [];
        this._importOptions = {};

        this.importTemplates = [];

        this.formattingOptionsValues = this._getCSVFormattingOptions();

        this.importOptionsValues = {
            ...this.formattingOptionsValues,
            advanced: {
                reloadParse: true,
                value: true,
            },
            has_headers: {
                reloadParse: true,
                value: true,
            },
            keep_matches: {
                value: false,
            },
            limit: {
                value: 2000,
            },
            sheets: {
                value: [],
            },
            sheet: {
                label: _t("Selected Sheet:"),
                reloadParse: true,
                value: "",
            },
            skip: {
                value: 0,
            },
            tracking_disable: {
                value: true,
            },
        };

        this.fieldsToHandle = {};
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get formattingOptions() {
        return pick(this.importOptionsValues, ...Object.keys(this.formattingOptionsValues));
    }

    get importOptions() {
        const tempImportOptions = {
            import_skip_records: [],
            import_set_empty_fields: [],
            fallback_values: {},
            name_create_enabled_fields: {},
        };
        for (const [name, option] of Object.entries(this.importOptionsValues)) {
            tempImportOptions[name] = ['date_format', 'datetime_format'].includes(name) && !option.value.includes('%')
                ? moment_to_strftime_format(option.value)
                : option.value;
        }

        for (const key in this.fieldsToHandle) {
            const value = this.fieldsToHandle[key];
            if (value) {
                if (value.optionName === "import_skip_records") {
                    tempImportOptions.import_skip_records.push(key);
                } else if (value.optionName === "import_set_empty_fields") {
                    tempImportOptions.import_set_empty_fields.push(key);
                } else if (value.optionName === "name_create_enabled_fields") {
                    tempImportOptions.name_create_enabled_fields[key] = true;
                } else if (value.optionName === "fallback_values") {
                    tempImportOptions.fallback_values[key] = value.value;
                }
            }
        }

        this._importOptions = tempImportOptions;
        return tempImportOptions;
    }

    set importOptions(options) {
        for (const key in options) {
            this.importOptionsValues[key].value = options[key];
        }
    }

    /**
     * A custom BlockUI is required to add the progress bar or text when blocking
     * the UI, without modifying the core ui service to handle a generic use case
     */
    block(message, blockComponent) {
        mainComponentRegistry.add(
            "ImportBlockUI",
            {
                Component: ImportBlockUI,
                props: {
                    blockComponent,
                    message,
                },
            },
            { force: true }
        );
    }

    unblock() {
        mainComponentRegistry.remove("ImportBlockUI");
    }

    async init() {
        [this.importTemplates, this.id] = await Promise.all([
            this.orm.call(this.resModel, "get_import_templates", [], {
                context: this.context,
            }),
            this.orm.call("base_import.import", "create", [{ res_model: this.resModel }]),
        ]);
    }

    async executeImport(isTest = false, totalSteps, importProgress) {
        this.handleInterruption = false;
        this._updateComments();
        this.importMessages = [];

        const startRow = this.importOptions.skip;
        const importRes = {
            ids: [],
            fields: this.columns.map((e) => Boolean(e.fieldInfo) && e.fieldInfo.fieldPath),
            columns: this.columns.map((e) => e.name.trim().toLowerCase()),
            hasError: false,
        };

        for (let i = 1; i <= totalSteps; i++) {
            if (this.handleInterruption) {
                if (importRes.hasError || isTest) {
                    importRes.nextrow = startRow;
                    this.setOption("skip", startRow);
                }
                break;
            }

            const error = await this._executeImportStep(isTest, importRes);
            if (error) {
                let message;
                const errorData = error.data || {};
                if (errorData.type === "xhrerror") {
                    const xhr = errorData.objects[0];
                    switch (xhr.status) {
                        case 504: // gateway timeout
                            message = _t(
                                "Import timed out. Please retry. If you still encounter this issue, the file may be too big for the system's configuration, try to split it (import less records per file)."
                            );
                            break;
                        default:
                            message = _t(
                                "An unknown issue occurred during import (possibly lost connection, data limit exceeded or memory limits exceeded). Please retry in case the issue is transient. If the issue still occurs, try to split the file rather than import it at once."
                            );
                    }
                } else {
                    message =
                        (errorData.arguments &&
                            (errorData.arguments[1] || errorData.arguments[0])) ||
                        error.message;
                }

                if (error.message) {
                    this._addMessage("danger", [error.message, message]);
                } else {
                    this._addMessage("danger", [message]);
                }

                importRes.hasError = true;
                break;
            }

            if (importProgress) {
                importProgress.step = i;
                importProgress.value = Math.round((100 * (i - 1)) / totalSteps);
            }
        }

        if (!importRes.hasError) {
            if (importRes.nextrow) {
                this._addMessage("warning", [
                    sprintf(
                        _t("Click 'Resume' to proceed with the import, resuming at line %s."),
                        importRes.nextrow + 1
                    ),
                    _t("You can test or reload your file before resuming the import."),
                ]);
            }
            if (isTest) {
                this._addMessage("info", [_t("Everything seems valid.")]);
            }
        } else {
            importRes.nextrow = startRow;
        }
        return { res: importRes };
    }

    /**
     * Ask the server for the parsing preview
     * and update the data accordingly.
     */
    async updateData(fileChanged = false) {
        if (fileChanged) {
            this.importOptionsValues.sheet.value = "";
        }
        this.importMessages = [];

        const res = await this.orm.call("base_import.import", "parse_preview", [
            this.id,
            this.importOptions,
        ]);

        if (!res.error) {
            this._onLoadSuccess(res);
        } else {
            this._onLoadError();
        }

        return { res, error: res.error };
    }

    async setOption(optionName, value, fieldName) {
        if (fieldName) {
            this.fieldsToHandle[fieldName] = {
                optionName,
                value,
            };
            return;
        }
        this.importOptionsValues[optionName].value = value;
        if (this.importOptionsValues[optionName].reloadParse) {
            await this.updateData();
        }
    }

    setColumnField(column, fieldInfo) {
        column.fieldInfo = fieldInfo;
        this._updateComments(column);
    }

    isColumnFieldSet(column) {
        return column.fieldInfo != null;
    }

    /*
     * We must wait the current iteration of execute_import to conclude and it
     * will stop at the start of the next batch with handleInterruption
     */
    stopImport() {
        this.handleInterruption = true;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _addMessage(type, lines) {
        const importMsgs = this.importMessages;
        importMsgs.push({
            type: type.replace("error", "danger"),
            lines,
        });
        this.importMessages = importMsgs;
    }

    async _executeImportStep(isTest, importRes) {
        const importArgs = [this.id, importRes.fields, importRes.columns, this.importOptions];
        const { ids, messages, nextrow, name, error } = await this._callImport(isTest, importArgs);

        // Handle server errors
        if (error) {
            return error;
        }

        if (ids) {
            importRes.ids = importRes.ids.concat(ids);
        }

        // Handle import errors
        if (messages && messages.length) {
            importRes.hasError = true;
            this.stopImport();
            if (this._handleImportErrors(messages, name)) {
                return false;
            }
        }

        this.setOption("skip", nextrow || 0);
        importRes.nextrow = nextrow;
        return false;
    }

    async _callImport(dryrun, args) {
        try {
            const res = await this.orm.silent.call("base_import.import", "execute_import", args, {
                dryrun,
                context: {
                    ...this.context,
                    tracking_disable: this.importOptions.tracking_disable,
                },
            });
            return res;
        } catch (error) {
            // This pattern isn't optimal but it is need to have
            // similar behaviours as in legacy. That is, catching
            // all import errors and showing them inside the top
            // "messages" area.
            return { error };
        }
    }

    _handleImportErrors(messages, name) {
        if (messages[0].not_matching_error) {
            this._addMessage(messages[0].type, [messages[0].message]);
            return true;
        }

        const sortedMessages = this._groupErrorsByField(messages);
        if (sortedMessages[0]) {
            this._addMessage(sortedMessages[0].type, [sortedMessages[0].message]);
            delete sortedMessages[0];
        } else {
            this._addMessage("danger", [_t("The file contains blocking errors (see below)")]);
        }

        for (const [columnFieldId, errors] of Object.entries(sortedMessages)) {
            // Handle errors regarding specific colums.
            const column = this.columns.find(
                (e) => e.fieldInfo && e.fieldInfo.fieldPath === columnFieldId
            );
            if (column) {
                column.resultNames = name;
                column.errors = errors;
            } else {
                for (const error of errors) {
                    // Handle errors regarding specific records.
                    if (error.record !== undefined) {
                        this._addMessage("danger", [
                            error.rows.from === error.rows.to
                                ? sprintf(_t('Error at row %s: "%s"'), error.record, error.message)
                                : sprintf(_t("%s at multiple rows"), error.message),
                        ]);
                    }
                    // Handle global errors.
                    else {
                        this._addMessage("danger", [error.message]);
                    }
                }
            }
        }
    }

    _groupErrorsByField(messages) {
        const groupedErrors = {};
        const errorsByMessage = groupBy(this._sortErrors(messages), (f) => f.message || "0");
        for (const [message, errors] of Object.entries(errorsByMessage)) {
            if (!message.record) {
                const foundError = errors.find((e) => e.record === undefined);
                if (foundError) {
                    groupedErrors[0] = foundError;
                    continue;
                }
            }

            errors[0].rows.to = errors[errors.length - 1].rows.to;
            const fieldId = errors[0].field_path ? errors[0].field_path.join("/") : errors[0].field;
            if (groupedErrors[fieldId]) {
                groupedErrors[fieldId].push(errors[0]);
            } else {
                groupedErrors[fieldId] = [errors[0]];
            }
        }
        return groupedErrors;
    }

    _sortErrors(messages) {
        return sortBy(messages, (e) => ["error", "warning", "info"].indexOf(e.priority));
    }

    /**
     * On the preview data succesfuly loaded, update the
     * import options, columns and messages.
     * @param {*} res
     */
    _onLoadSuccess(res) {
        // Set options
        for (const key in res.options) {
            if (this.importOptionsValues[key]) {
                this.importOptionsValues[key].value = res.options[key];
            }
        }

        if (!res.fields.length) {
            this.importOptionsValues.advanced.value = res.advanced_mode;
        }

        this.fields = res.fields;
        this.columns = this._getColumns(res);

        // Set import messages
        if (res.headers.length === 1) {
            this._addMessage("warning", [
                _t(
                    "A single column was found in the file, this often means the file separator is incorrect."
                ),
            ]);
        }

        this._updateComments();
    }

    _onLoadError() {
        this.columns = [];
        this.importMessages = [];
    }

    _getColumns(res) {
        function getId(res, index) {
            return res.matches && index in res.matches && res.matches[index].length > 0
                ? res.matches[index].join("/")
                : undefined;
        }

        if (this.importOptions.has_headers && res.headers && res.preview.length > 0) {
            return res.headers.flatMap((header, index) => {
                return this._createColumn(
                    res,
                    getId(res, index),
                    header,
                    index,
                    res.preview[index],
                    res.preview[index][0]
                );
            });
        } else if (res.preview && res.preview.length >= 2) {
            return res.preview.flatMap((preview, index) =>
                this._createColumn(
                    res,
                    preview[0],
                    this.importOptions.has_headers ? preview[0] : preview.join(", "),
                    index,
                    preview,
                    preview[1]
                )
            );
        }
        return [];
    }

    _createColumn(res, id, name, index, previews, preview) {
        const fields = this._getFields(res, index);
        return {
            id,
            name,
            preview,
            previews,
            fields,
            fieldInfo: this._findField(fields, id),
            comments: [],
            errors: [],
        };
    }

    _findField(fields, id) {
        return Object.entries(fields)
            .flatMap((e) => e[1])
            .find((field) => field.fieldPath === id);
    }

    /**
     * Sort fields into their respective categories, namely:
     * - Basic => Only the ID field
     * - Suggested => Non-relational fields from the header"s types
     * - Additional => Non-relational fields of any other type
     * - Relational => Relational fields
     * @param {*} res
     */
    _getFields(res, index) {
        const advanced = this.importOptionsValues.advanced.value;
        const fields = {
            basic: [],
            suggested: [],
            additional: [],
            relational: [],
        };

        function isRegular(subfields) {
            return (
                !subfields ||
                subfields.length === 0 ||
                (subfields.length === 2 &&
                    subfields[0].name === "id" &&
                    subfields[1].name === ".id")
            );
        }

        function hasType(types, field) {
            return types && types.indexOf(field.type) !== -1;
        }

        const sortSingleField = (field, ancestors, collection, types) => {
            ancestors.push(field);
            field.fieldPath = ancestors.map((f) => f.name).join("/");
            field.label = ancestors.map((f) => f.string).join(" / ");

            // Get field respective category
            if (!collection) {
                if (field.name === "id") {
                    collection = fields.basic;
                } else if (isRegular(field.fields)) {
                    collection = hasType(types, field) ? fields.suggested : fields.additional;
                } else {
                    collection = fields.relational;
                }
            }

            // Add field to found category
            collection.push(field);

            if (advanced) {
                for (const subfield of field.fields) {
                    sortSingleField(subfield, [...ancestors], collection, types);
                }
            }
        };

        // Sort fields in their respective categories
        for (const field of this.fields) {
            if (!field.isRelation) {
                if (advanced) {
                    sortSingleField(field, [], undefined, ["all"]);
                } else {
                    const acceptedTypes = res.header_types[index];
                    sortSingleField(field, [], undefined, acceptedTypes);
                }
            }
        }

        return fields;
    }

    _updateComments(updatedColumn) {
        for (const column of this.columns) {
            column.comments = [];
            column.errors = [];
            column.resultNames = [];
            column.importOptions =
                column.fieldInfo && this.fieldsToHandle[column.fieldInfo.fieldPath];

            if (!column.fieldInfo) {
                continue;
            }

            // Fields of type "char", "text" or "many2many" can be specified multiple
            // times and they will be concatenated, fields of other types must be unique.
            if (["char", "text", "many2many"].includes(column.fieldInfo.type)) {
                if (column.fieldInfo.type === "many2many") {
                    column.comments.push({
                        type: "info",
                        content: _t("To import multiple values, separate them by a comma."),
                    });
                }

                // If multiple columns are mapped on the same field, inform
                // the user that they will be concatenated.
                const samefieldColumns = this.columns.filter(
                    (col) => col.fieldInfo && col.fieldInfo.fieldPath === column.fieldInfo.fieldPath
                );
                if (samefieldColumns.length >= 2) {
                    column.comments.push({
                        type: "info",
                        content: _t("This column will be concatenated in field"),
                        fieldName: column.fieldInfo.string,
                    });
                }
            } else if (updatedColumn && column.id !== updatedColumn.id && updatedColumn.fieldInfo) {
                // If column is mapped on an already mapped field, remove that field
                // from the old column to keep it unique.
                if (updatedColumn.fieldInfo.fieldPath === column.fieldInfo.fieldPath) {
                    column.fieldInfo = null;
                }
            }
        }
    }

    _getCSVFormattingOptions() {
        return {
            encoding: {
                label: _t("Encoding:"),
                type: "select",
                value: "",
                options: [
                    "utf-8",
                    "utf-16",
                    "windows-1252",
                    "latin1",
                    "latin2",
                    "big5",
                    "gb18030",
                    "shift_jis",
                    "windows-1251",
                    "koi8_r",
                ],
            },
            separator: {
                label: _t("Separator:"),
                type: "select",
                value: "",
                options: [
                    { value: ",", label: _t("Comma") },
                    { value: ";", label: _t("Semicolon") },
                    { value: "\t", label: _t("Tab") },
                    { value: " ", label: _t("Space") },
                ],
            },
            quoting: {
                label: _t("Text Delimiter:"),
                type: "input",
                value: '"',
                options: "",
            },
            date_format: {
                label: _t("Date Format:"),
                type: "select",
                value: "",
                options: [
                    "YYYY-MM-DD",
                    "DD/MM/YY",
                    "DD/MM/YYYY",
                    "DD-MM-YYYY",
                    "DD-MMM-YY",
                    "DD-MMM-YYYY",
                    "MM/DD/YY",
                    "MM/DD/YYYY",
                    "MM-DD-YY",
                    "MM-DD-YYYY",
                    "DDMMYY",
                    "DDMMYYYY",
                    "YYMMDD",
                    "YYYYMMDD",
                    "YY/MM/DD",
                    "YYYY/MM/DD",
                    "MMDDYY",
                    "MMDDYYYY",
                ],
            },
            datetime_format: {
                label: _t("Datetime Format:"),
                type: "input",
                value: "",
                options: "",
            },
            float_thousand_separator: {
                label: _t("Thousands Separator:"),
                type: "select",
                value: ",",
                options: [
                    { value: ",", label: _t("Comma") },
                    { value: ".", label: _t("Dot") },
                    { value: "", label: _t("No Separator") },
                ],
            },
            float_decimal_separator: {
                label: _t("Decimals Separator:"),
                type: "select",
                value: ".",
                options: [
                    { value: ",", label: _t("Comma") },
                    { value: ".", label: _t("Dot") },
                ],
            },
        };
    }
}

/**
 * @returns {BaseImportModel}columns
 */
export function useImportModel({ env, resModel, context, orm }) {
    return useState(new BaseImportModel({ env, resModel, context, orm }));
}
