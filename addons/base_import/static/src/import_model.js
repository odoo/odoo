import { proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { sortBy } from "@web/core/utils/arrays";
import { checkFileSize, DEFAULT_MAX_FILE_SIZE } from "@web/core/utils/files";
import { memoize } from "@web/core/utils/functions";
import { useService } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";
import { session } from "@web/session";
import { ImportBlockUI } from "./import_block_ui";
import { BinaryFileManager } from "./binary_file_manager";

const mainComponentRegistry = registry.category("main_components");

export const IMPORT_LANGUAGE_SEPARATOR = `@`;

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
    constructor({ env, context, orm }) {
        this.id = 1;
        this.env = env;
        this.orm = orm;
        this.handleInterruption = false;

        this.context = context || {};

        this.fields = [];
        this.columns = [];
        this.importMessages = [];

        this.importTemplates = [];

        this.formattingOptionsValues = this._getCSVFormattingOptions();

        this.importOptionsValues = {
            ...this.formattingOptionsValues,
            advanced: {
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
                help: _t("Defines how many megabytes can be imported in each batch"),
                value: 10,
                max: Math.round(maxUploadSize / 1024 / 1024),
                min: 0,
            },
            delayAfterEachBatch: {
                help: _t("Delay applied after each batch to prevent unthrottled calls"),
                value: 1,
                min: 1,
            },
        };

        // by identity, kept across runs as long as they are reported or resolved
        this.errors = {};
        this.resultNames = [];

        this.languagesInstalled = [];

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
            name_create_enabled_fields: {},
        };
        for (const [name, option] of Object.entries(this.importOptionsValues)) {
            tempImportOptions[name] = option.value;
        }
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

    setResModel(resModel) {
        this.resModel = resModel;
    }

    async init() {
        [this.importTemplates, this.id, this.languagesInstalled] = await Promise.all([
            this.orm.call(this.resModel, "get_import_templates", [], {
                context: this.context,
            }),
            this.orm.call("base_import.import", "create", [{ res_model: this.resModel }]),
            this.orm.call("res.lang", "get_installed", []),
        ]);
    }

    getFinalFieldName(field) {
        let name = Boolean(field.fieldInfo) && field.fieldInfo.fieldPath;
        if (name && field.language) {
            name += `${IMPORT_LANGUAGE_SEPARATOR}${field.language}`;
        }
        return name;
    }

    async executeImport(isTest = false, totalSteps, importProgress) {
        this.handleInterruption = false;
        this._updateComments();
        this.importMessages = [];
        for (const error of Object.values(this.errors)) {
            error.outdated = true;
        }

        const startRow = this.importOptions.skip;
        const importRes = {
            ids: [],
            fields: this.columns.map((e) => this.getFinalFieldName(e)),
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
                const message =
                    (errorData.arguments && (errorData.arguments[1] || errorData.arguments[0])) ||
                    _t(
                        "An unknown issue occurred during import (possibly lost connection, data limit exceeded or memory limits exceeded). Please retry in case the issue is transient. If the issue still occurs, try to split the file rather than import it at once."
                    );

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

        // resolved errors stay displayed, so that their resolution can be changed
        for (const [key, error] of Object.entries(this.errors)) {
            if (error.outdated && !error.resolution) {
                delete this.errors[key];
            }
        }
        this._dispatchErrors();

        if (!importRes.hasError) {
            if (!isTest && importRes.nextrow) {
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
                this.setOption("skip", 0);
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
            this.errors = {};
            this.resultNames = [];
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

    async setOption(optionName, value) {
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
        if (column.fieldInfo) {
            this._forgetErrors(column.fieldInfo.fieldPath);
        }
        column.fieldInfo = fieldInfo;
        this._updateComments(column);
    }

    /**
     * @param {Object} error as reported by the server
     * @param {Object|false} resolution `{ action: "empty"|"set", value }`
     */
    setErrorResolution(error, resolution) {
        error.resolution = resolution;
    }

    setColumnLanguage(column, language) {
        column.language = language;
        this._updateComments(column);
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
            // kept out of the options, so that resolving an error does not
            // re-render every component watching them
            { ...this.formattedImportOptions, ...this._getErrorResolutions() },
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
            importRes.nextrow = 0;
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
        this.resultNames = name || [];
        if (messages[0].not_matching_error) {
            const [error] = this._registerErrors(messages);
            if (error.value !== undefined && this._findErrorColumn(error)) {
                this.notificationService.add(_t("Import failed: see errors below"), {
                    type: "danger",
                    autocloseDelay: 4000,
                });
            } else {
                this._addMessage(error.type, [error.message]);
            }
            return true;
        }

        const errors = this._registerErrors(this._mergeErrors(messages));
        const globalErrors = errors.filter((error) => error.record === undefined);
        for (const error of globalErrors) {
            this._addMessage(error.type, [error.message]);
        }
        if (!globalErrors.length) {
            this.notificationService.add(_t("Import failed: see errors below"), {
                type: "danger",
                autocloseDelay: 4000,
            });
        }
        for (const error of errors) {
            if (error.record !== undefined && !this._findErrorColumn(error)) {
                this._addMessage("danger", [this._getErrorText(error)]);
            }
        }
    }

    /**
     * Merge the errors sharing the same message and offending value into a
     * single one spanning all their rows.
     */
    _mergeErrors(messages) {
        const sorted = sortBy(messages, (e) => ["error", "warning", "info"].indexOf(e.type));
        const byMessage = Object.groupBy(sorted, (e) =>
            JSON.stringify([e.message || "", e.value ?? null])
        );
        return Object.values(byMessage).map((errors) => {
            const global = errors.find((e) => e.record === undefined);
            if (global || !errors[0].rows) {
                return global || errors[0];
            }
            return { ...errors[0], rows: { ...errors[0].rows, to: errors.at(-1).rows.to } };
        });
    }

    _registerErrors(errors) {
        for (const error of errors) {
            const key = this._getErrorKey(error);
            const previous = this.errors[key];
            error.resolution = previous?.resolution || false;
            error.reportedBefore = Boolean(previous);
            this.errors[key] = error;
        }
        return errors;
    }

    _getErrorKey(error) {
        return error.value === undefined
            ? `${error.message}@${error.rows?.from}`
            : `${this._getErrorFieldPath(error)}:${error.value}`;
    }

    _getErrorFieldPath(error) {
        return error.field_path ? error.field_path.join("/") : error.field;
    }

    _findErrorColumn(error) {
        const fieldPath = this._getErrorFieldPath(error);
        if (!fieldPath) {
            return undefined;
        }
        return this.columns.find((column) => column.fieldInfo?.fieldPath === fieldPath);
    }

    _getErrorText(error) {
        return error.rows.from === error.rows.to
            ? _t('Error at row %(row)s: "%(error)s"', {
                  row: error.rows.from + 1,
                  error: error.message,
              })
            : _t('Error at rows %(from)s to %(to)s: "%(error)s"', {
                  from: error.rows.from + 1,
                  to: error.rows.to + 1,
                  error: error.message,
              });
    }

    _forgetErrors(fieldPath) {
        for (const [key, error] of Object.entries(this.errors)) {
            if (this._getErrorFieldPath(error) === fieldPath) {
                delete this.errors[key];
            }
        }
    }

    _dispatchErrors() {
        const errors = Object.values(this.errors);
        for (const column of this.columns) {
            column.errors = column.fieldInfo
                ? errors.filter(
                      (error) => this._getErrorFieldPath(error) === column.fieldInfo.fieldPath
                  )
                : [];
        }
    }

    _getErrorResolutions() {
        const resolutions = {};
        for (const error of Object.values(this.errors)) {
            const fieldPath = this._getErrorFieldPath(error);
            if (!error.resolution || !fieldPath || error.value === undefined) {
                continue;
            }
            resolutions[fieldPath] = {
                ...resolutions[fieldPath],
                [error.value]: error.resolution,
            };
        }
        return { resolutions };
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
            return res.headers.flatMap((header, index) =>
                this._createColumn(
                    res,
                    getId(res, index),
                    header,
                    index,
                    res.preview[index],
                    res.preview[index][0],
                    this.languagesInstalled.find((val) => val[0] === res.languages[index])
                        ? res.languages[index]
                        : null
                )
            );
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

    _createColumn(res, id, name, index, previews, preview, language = null) {
        const fields = this._getFields(res, index);
        return {
            id,
            name,
            preview,
            previews,
            fields,
            language,
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
            required: [],
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
            if (!collection || collection === fields.required) {
                if (field.name === "id" && ancestors.length === 1) {
                    collection = fields.basic;
                } else if (field.required && ancestors.length === 1) {
                    collection = fields.required;
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
        const userLanguage = user.lang.replace("-", "_");
        const translatedColumns = new Set();
        for (const column of this.columns) {
            if (column.fieldInfo && this.languagesInstalled.length > 1 && column.language) {
                translatedColumns.add(column.fieldInfo.fieldPath);
            }
        }
        for (const column of this.columns) {
            column.comments = [];

            if (!column.fieldInfo) {
                continue;
            }
            if (
                column.fieldInfo.name === "id" &&
                column.previews.some((p) => Number.isInteger(Number(p)))
            ) {
                column.comments.push({
                    type: "warning",
                    content: _t(
                        `Use unique key across objects for External ID's, for example "lead_1" instead of "1"`
                    ),
                });
            }
            // Fields of type "char", "text" or "many2many" can be specified multiple
            // times and they will be concatenated, fields of other types must be unique.
            if (["char", "text", "html", "many2many"].includes(column.fieldInfo.type)) {
                if (column.fieldInfo.type === "many2many") {
                    column.comments.push({
                        type: "info",
                        content: _t("To import multiple values, separate them by a comma."),
                    });
                }

                // If multiple columns are mapped on the same field, inform
                // the user that they will be concatenated.
                const samefieldColumns = this.columns.filter(
                    (col) =>
                        col.fieldInfo &&
                        col.fieldInfo.fieldPath === column.fieldInfo.fieldPath &&
                        (this.languagesInstalled.length === 1 ||
                            (col.language ?? userLanguage) === (column.language ?? userLanguage))
                );
                if (samefieldColumns.length >= 2) {
                    column.comments.push({
                        type: "info",
                        content: _t("This column will be concatenated in field"),
                        fieldName: column.fieldInfo.string,
                        lang: this.languagesInstalled.find(
                            (val) => val[0] === (column.language ?? userLanguage)
                        )?.[1],
                    });
                }
                column.translatedColumn = translatedColumns.has(column.fieldInfo.fieldPath);
            } else if (updatedColumn && column.id !== updatedColumn.id && updatedColumn.fieldInfo) {
                // If column is mapped on an already mapped field, remove that field
                // from the old column to keep it unique.
                if (updatedColumn.fieldInfo.fieldPath === column.fieldInfo.fieldPath) {
                    column.fieldInfo = null;
                }
            }
        }
        this._dispatchErrors();
    }

    _getCSVFormattingOptions() {
        return {
            encoding: {
                label: _t("Encoding"),
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
                label: _t("Separator"),
                type: "select",
                value: "",
                options: [
                    { value: "", label: _t("Other") },
                    { value: ",", label: _t("Comma") },
                    { value: ";", label: _t("Semicolon") },
                    { value: "\t", label: _t("Tab") },
                    { value: " ", label: _t("Space") },
                ],
                other: [",", ";", "\t", " "],
            },
            quoting: {
                label: _t("Delimiter"),
                type: "input",
                value: '"',
            },
            float_thousand_separator: {
                label: _t("Thousands Separator"),
                type: "select",
                value: ",",
                options: [
                    { value: ",", label: _t("Comma") },
                    { value: ".", label: _t("Dot") },
                    { value: "", label: _t("No Separator") },
                ],
            },
            float_decimal_separator: {
                label: _t("Decimals Separator"),
                type: "select",
                value: ".",
                options: [
                    { value: ",", label: _t("Comma") },
                    { value: ".", label: _t("Dot") },
                ],
            },
            date_format: {
                label: _t("Date Format"),
                help: _t(
                    "Use YYYY to represent the year, MM for the month and DD for the day. Include separators such as a dot, forward slash or dash. You can use a custom format in addition to the suggestions provided. Leave empty to let Odoo guess the format (recommended)"
                ),
                type: "input",
                value: "",
                placeholder: _t("No date detected"),
                options: [
                    "DD/MM/YYYY",
                    "MM/DD/YYYY",
                    "YYYY/MM/DD",
                    "DD-MM-YYYY",
                    "MM-DD-YYYY",
                    "YYYY-MM-DD",
                    "DD.MM.YYYY",
                    "MM.DD.YYYY",
                    "YYYY.MM.DD",
                ],
            },
            datetime_format: {
                label: _t("Datetime Format"),
                help: _t(
                    "Use HH for hours in a 24h system, use II in conjonction with 'p' for a 12h system. You can use a custom format in addition to the suggestions provided. Leave empty to let Odoo guess the format (recommended)"
                ),
                type: "input",
                value: "",
                placeholder: _t("No datetime detected"),
                options: [
                    "YYYY-MM-DD HH:mm:SS",
                    "YYYY/MM/DD HH:mm:SS",
                    "DD/MM/YYYY HH:mm:SS",
                    "DDMMYYYY HH:mm:SS",
                    "MM/DD/YYYY II:mm:SS p",
                    "MMDDYYYY II:mm:SS p",
                ],
            },
        };
    }
}

/**
 * @returns {BaseImportModel}columns
 */
export function useImportModel({ env, context }) {
    const orm = useService("orm");
    return proxy(new BaseImportModel({ env, context, orm }));
}
