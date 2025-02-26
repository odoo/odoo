import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Cache } from "@web/core/utils/cache";

/**
 * @typedef {Object} LoadFieldsOptions
 * @property {string[]|false} [fieldNames]
 * @property {string[]} [attributes]
 */

// see READ_GROUP_NUMBER_GRANULARITY in odoo/orm/utils.py
export const DATETIME_OPTIONS = Object.fromEntries(
    Object.entries({
        second_number: { string: _t("Second number") },
        minute_number: { string: _t("Minute number") },
        hour_number: { string: _t("Hour number") },
        iso_week_number: { string: _t("Week number") },
        month_number: { string: _t("Month number") },
        quarter_number: { string: _t("Quarter number") },
        day_of_year: { string: _t("Day of year") },
        day_of_month: { string: _t("Day of month") },
        day_of_week: { string: _t("Day of week") },
    }).map(([name, o]) => [name, { ...o, searchable: true, name, type: "datetimeOption" }])
);

export const fieldService = {
    dependencies: ["orm"],
    async: ["loadFields", "loadPath", "loadPropertyDefinitions"],
    start(env, { orm }) {
        const cache = new Cache(
            (resModel, options) =>
                orm
                    .call(resModel, "fields_get", [options.fieldNames, options.attributes])
                    .catch((error) => {
                        cache.clear(resModel, options);
                        return Promise.reject(error);
                    }),
            (resModel, options) =>
                JSON.stringify([resModel, options.fieldNames, options.attributes])
        );

        env.bus.addEventListener("CLEAR-CACHES", () => cache.invalidate());

        /**
         * @param {string} resModel
         * @param {LoadFieldsOptions} [options]
         * @returns {Promise<object>}
         */
        async function loadFields(resModel, options = {}) {
            if (typeof resModel !== "string" || !resModel) {
                throw new Error(`Invalid model name: ${resModel}`);
            }
            return cache.read(resModel, options);
        }

        /**
         * @param {Object} fieldDefs
         * @param {string} name
         * @param {import("@web/core/domain").DomainListRepr} [domain=[]]
         * @returns {Promise<Object>}
         */
        async function _loadPropertyDefinitions(fieldDefs, name, domain = []) {
            const {
                definition_record: definitionRecord,
                definition_record_field: definitionRecordField,
            } = fieldDefs[name];
            const definitionRecordModel = fieldDefs[definitionRecord].relation;

            domain = Domain.and([[[definitionRecordField, "!=", false]], domain]).toList();

            const result = await orm.webSearchRead(definitionRecordModel, domain, {
                specification: {
                    display_name: {},
                    [definitionRecordField]: {},
                },
            });

            const definitions = {};
            for (const record of result.records) {
                for (const definition of record[definitionRecordField]) {
                    definitions[definition.name] = {
                        is_property: true,
                        // for now, all properties are searchable but their definitions don't contain that info
                        searchable: true,
                        // differentiate definitions with same name but on different parent
                        record_id: record.id,
                        record_name: record.display_name,
                        ...definition,
                    };
                }
            }
            return definitions;
        }

        /**
         * @param {string} resModel
         * @param {string} fieldName
         * @param {import("@web/core/domain").DomainListRepr} [domain]
         * @returns {Promise<object[]>}
         */
        async function loadPropertyDefinitions(resModel, fieldName, domain) {
            const fieldDefs = await loadFields(resModel);
            return _loadPropertyDefinitions(fieldDefs, fieldName, domain);
        }

        /**
         * @param {string|null} resModel valid model name or null (case virtual)
         * @param {Object|null} fieldDefs
         * @param {string[]} names
         */
        async function _loadPath(resModel, fieldDefs, names) {
            if (!fieldDefs) {
                return { isInvalid: "path", names, modelsInfo: [] };
            }

            const [name, ...remainingNames] = names;
            const modelsInfo = [{ resModel, fieldDefs }];
            if (resModel === "*" && remainingNames.length) {
                return { isInvalid: "path", names, modelsInfo };
            }

            const fieldDef = fieldDefs[name];
            if ((name !== "*" && !fieldDef) || (name === "*" && remainingNames.length)) {
                return { isInvalid: "path", names, modelsInfo };
            }

            if (!remainingNames.length) {
                return { names, modelsInfo };
            }

            let subResult;
            if (fieldDef.relation) {
                subResult = await _loadPath(
                    fieldDef.relation,
                    await loadFields(fieldDef.relation),
                    remainingNames
                );
            } else if (fieldDef.type === "properties") {
                subResult = await _loadPath(
                    "*",
                    await _loadPropertyDefinitions(fieldDefs, name),
                    remainingNames
                );
            } else if (fieldDef.type === "datetime") {
                subResult = await _loadPath("*", { ...DATETIME_OPTIONS }, remainingNames);
            }

            if (subResult) {
                const result = {
                    names,
                    modelsInfo: [...modelsInfo, ...subResult.modelsInfo],
                };
                if (subResult.isInvalid) {
                    result.isInvalid = "path";
                }
                return result;
            }

            return { isInvalid: "path", names, modelsInfo };
        }

        /**
         * Note: the symbol * can be used at the end of path (e.g path="*" or path="user_id.*").
         * It says to load the fields of the appropriate model.
         * @param {string} resModel
         * @param {string} path
         * @returns {Promise<Object>}
         */
        async function loadPath(resModel, path = "*") {
            const fieldDefs = await loadFields(resModel);
            if (typeof path !== "string" || !path) {
                throw new Error(`Invalid path: ${path}`);
            }
            return _loadPath(resModel, fieldDefs, path.split("."));
        }

        return { loadFields, loadPath, loadPropertyDefinitions };
    },
};

registry.category("services").add("field", fieldService);
