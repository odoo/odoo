/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { checkFileSize, DEFAULT_MAX_FILE_SIZE } from "@web/core/utils/files";
import { useService } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";
import { groupBy, sortBy } from "@web/core/utils/arrays";
import { memoize } from "@web/core/utils/functions";
import { session } from "@web/session";
import { useState } from "@odoo/owl";
import { ImportBlockUI } from "./import_block_ui";
import { BinaryFileManager } from "./binary_file_manager";

const mainComponentRegistry = registry.category("main_components");

const strftimeFormatTable = {
    d: "w",
    DD: "d",
    ddd: "a",
    dddd: "A",
    DDDD: "j",
    ww: "U",
    WW: "W",
    mm: "M",
    MM: "m",
    MMM: "b",
    MMMM: "B",
    YYYY: "Y",
    YY: "y",
    ss: "S",
    hh: "h",
    HH: "H",
    A: "p",
};

/**
 * Convert a human readable format to Python strftime format. In case
 * no corresponding format is supported, a similar fallback is given
 * from the list of other supported formatting value.
 *
 * @param {string} value original Luxon format
 * @returns {string} valid strftime format
 */
const humanToStrftimeFormat = memoize(function humanToStrftimeFormat(value) {
    const regex = /(dddd|ddd|dd|d|mmmm|mmm|mm|ww|yyyy|yy|hh|ss|a)/gi;
    return value.replace(regex, (value) => {
        if (strftimeFormatTable[value]) {
            return "%" + strftimeFormatTable[value];
        }
        return (
            "%" +
            (strftimeFormatTable[value.toLowerCase()] || strftimeFormatTable[value.toUpperCase()])
        );
    });
});

const strftimeToHumanFormat = memoize(function strftimeToHumanFormat(value) {
    Object.entries(strftimeFormatTable).forEach(([k, v]) => {
        value = value.replace(`%${v}`, k);
    });
    return value;
});

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

        const maxUploadSize = session.max_file_upload_size || DEFAULT_MAX_FILE_SIZE;
        this.binaryFilesParams = {
            binaryFiles: {
                value: {},
            },
            maxSizePerBatch: {
                help: _t("Defines how many megabytes can be imported in each batch import"),
                value: 10,
                max: Math.round(maxUploadSize / 1024 / 1024),
                min: 0,
            },
            delayAfterEachBatch: {
                help: _t(
                    "After each batch import, this delay is applied to avoid unthrottled calls"
                ),
                value: 1,
                min: 1,
            },
        };

        this.fieldsToHandle = {};

        this.notificationService = useService("notification");
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get formattingOptions() {
        return pick(this.importOptionsValues, ...Object.keys(this.formattingOptionsValues));
    }

    /**
     * This getter returns the current values pf the options, formatted to match the
     * server API (date and datetime options should be Python strftime formatted)
     */
    get formattedImportOptions() {
        const options = this.importOptions;
        options.date_format = humanToStrftimeFormat(options.date_format);
        options.datetime_format = humanToStrftimeFormat(options.datetime_format);
        return options;
    }

    get importOptions() {
        const tempImportOptions = {
            import_skip_records: [],
            import_set_empty_fields: [],
            fallback_values: {},
            name_create_enabled_fields: {},
        };
        for (const [name, option] of Object.entries(this.importOptionsValues)) {
            tempImportOptions[name] = option.value;
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
                const errorData = error.data || {};
                const message = errorData.arguments && (errorData.arguments[1] || errorData.arguments[0])
                    || _t("An unknown issue occurred during import (possibly lost connection, data limit exceeded or memory limits exceeded). Please retry in case the issue is transient. If the issue still occurs, try to split the file rather than import it at once.");

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
                    _t(
                        "Click 'Resume' to proceed with the import, resuming at line %s.",
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
            this.formattedImportOptions,
        ]);

        if (!res.error) {
            res.options.date_format = strftimeToHumanFormat(res.options.date_format);
            res.options.datetime_format = strftimeToHumanFormat(res.options.datetime_format);
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
            return this.updateData();
        }
    }

    onBinaryFilesParamsChanged(parameterName, value) {
        if (parameterName === "binaryFiles") {
            const files = {};
            for (const file of value) {
                if (checkFileSize(file.size, this.notificationService)) {
                    files[file.name] = file;
                }
            }
            value = files;
        }
        this.binaryFilesParams[parameterName].value = value;
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
        const importArgs = [
            this.id,
            importRes.fields,
            importRes.columns,
            this.formattedImportOptions,
        ];
        const { ids, messages, nextrow, name, error, binary_filenames } = await this._callImport(
            isTest,
            importArgs
        );

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

        // Push local image to records
        await this._pushLocalImageToRecords(ids, binary_filenames, isTest);

        // Check if we should continue
        if (nextrow) {
            this.setOption("skip", nextrow);
            importRes.nextrow = nextrow;
        } else {
            // Falsy `nextrow` signals there's nothing left to import
            this.stopImport();
        }
        return false;
    }

    async _pushLocalImageToRecords(ids, binaryFilenames, isTest) {
        if (typeof binaryFilenames === "object") {
            const parameters = {
                tracking_disable: this.importOptions.tracking_disable,
                delayAfterEachBatch: this.binaryFilesParams.delayAfterEachBatch.value,
                maxBatchSize: this.binaryFilesParams.maxSizePerBatch.value * 1024 * 1024,
            };

            if (!this.binaryFilesParams.binaryFiles) {
                return;
            }
            const binaryFiles = this.binaryFilesParams.binaryFiles.value;
            const fields = Object.keys(binaryFilenames);
            const binaryFileManager = new BinaryFileManager(
                this.resModel,
                fields,
                parameters,
                this.context,
                this.orm,
                this.notificationService
            );
            for (let rowIndex = 0; rowIndex < ids.length; rowIndex++) {
                const id = ids[rowIndex];
                for (const field of fields) {
                    const fileName = binaryFilenames[field][rowIndex];
                    if (!fileName) {
                        continue;
                    }
                    if (fileName in binaryFiles) {
                        const file = binaryFiles[fileName];
                        if (!file || isTest) {
                            continue;
                        }
                        await binaryFileManager.addFile(id, field, file);
                    }
                }
            }
            if (!isTest) {
                await binaryFileManager.sendLastPayload();
            }
        }
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
                                ? _t('Error at row %(row)s: "%(error)s"', {
                                      row: error.record,
                                      error: error.message,
                                  })
                                : _t("%s at multiple rows", error.message),
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
            },
            date_format: {
                help: _t(
                    "Use YYYY to represent the year, MM for the month and DD for the day. Include separators such as a dot, forward slash or dash. You can use a custom format in addition to the suggestions provided. Leave empty to let Odoo guess the format (recommended)"
                ),
                label: _t("Date Format:"),
                type: "input",
                value: "",
                options: [
                    "YYYY-MM-DD",
                    "YYYY/MM/DD",
                    "DD/MM/YYYY",
                    "DDMMYYYY",
                    "MM/DD/YYYY",
                    "MMDDYYYY",
                ],
            },
            datetime_format: {
                help: _t(
                    "Use HH for hours in a 24h system, use II in conjonction with 'p' for a 12h system. You can use a custom format in addition to the suggestions provided. Leave empty to let Odoo guess the format (recommended)"
                ),
                label: _t("Datetime Format:"),
                type: "input",
                value: "",
                options: [
                    "YYYY-MM-DD HH:mm:SS",
                    "YYYY/MM/DD HH:mm:SS",
                    "DD/MM/YYYY HH:mm:SS",
                    "DDMMYYYY HH:mm:SS",
                    "MM/DD/YYYY II:mm:SS p",
                    "MMDDYYYY II:mm:SS p",
                ],
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
