import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Cache } from "@web/core/utils/cache";
import { deepCopy } from "@web/core/utils/objects";

/**
 * @typedef {Object} LoadFieldsOptions
 * @property {string[]|false} [fieldNames]
 * @property {string[]} [attributes]
 */

const MODEL_DATETIME_PROPERTIES = Symbol("__model__datetime_PROPERTIES__");
const DATETIME_PROPERTIES = Object.fromEntries(
    Object.entries({
        __date: { string: _t("Date") }, // virtual: defined via year_number, month_number, and day_of_month
        __time: { string: _t("Time") }, // virtual: defined via hour_number, minute_number, and second_number
    }).map(([name, o]) => [name, { ...o, searchable: true, name, type: "datetime_option" }])
);

const MODEL_TIME_PROPERTIES = Symbol("__model__time_PROPERTIES__");
const TIME_PROPERTIES = Object.fromEntries(
    Object.entries({
        hour_number: { string: _t("Hour") },
        minute_number: { string: _t("Minute") },
        second_number: { string: _t("Second") },
    }).map(([name, o]) => [name, { ...o, searchable: true, name, type: "time_option" }])
);

const MODEL_DATE_PROPERTIES = Symbol("__model__date_PROPERTIES__");
const DATE_PROPERTIES = Object.fromEntries(
    Object.entries({
        year_number: { string: _t("Year") },
        quarter_number: { string: _t("Quarter") },
        month_number: { string: _t("Month") },
        iso_week_number: { string: _t("Week number") },
        day_of_year: { string: _t("Day of year") },
        day_of_month: { string: _t("Day of month") },
        day_of_week: { string: _t("Weekday") },
    }).map(([name, o]) => [name, { ...o, searchable: true, name, type: "date_option" }])
);

export const MODEL_SYMBOLS = new Set([
    MODEL_DATETIME_PROPERTIES,
    MODEL_DATE_PROPERTIES,
    MODEL_TIME_PROPERTIES,
]);
function getSpecialModelFields(resModel) {
    switch (resModel) {
        case MODEL_DATETIME_PROPERTIES:
            return Object.assign(
                {},
                deepCopy(DATETIME_PROPERTIES),
                deepCopy(DATE_PROPERTIES),
                deepCopy(TIME_PROPERTIES)
            );
        case MODEL_DATE_PROPERTIES:
            return deepCopy(DATE_PROPERTIES);
        case MODEL_TIME_PROPERTIES:
            return deepCopy(TIME_PROPERTIES);
    }
}

function getRelation(fieldDef) {
    if (fieldDef.relation) {
        return fieldDef.relation;
    }
    if (fieldDef.type === "datetime") {
        return MODEL_DATETIME_PROPERTIES;
    }
    if (fieldDef.type === "date" || fieldDef.name === "__date") {
        return MODEL_DATE_PROPERTIES;
    }
    if (fieldDef.name === "__time") {
        return MODEL_TIME_PROPERTIES;
    }
    return null;
}

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
         * @param {string|Symbol} resModel
         * @param {LoadFieldsOptions} [options]
         * @returns {Promise<object>}
         */
        async function loadFields(resModel, options = {}) {
            if (typeof resModel === "symbol" && MODEL_SYMBOLS.has(resModel)) {
                return getSpecialModelFields(resModel);
            }
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

            // @ts-ignore
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
         * @param {string|Symbol|null} resModel valid model name or null (case virtual)
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
            const relation = getRelation(fieldDef);
            if (relation) {
                subResult = await _loadPath(relation, await loadFields(relation), remainingNames);
            } else if (fieldDef.type === "properties") {
                subResult = await _loadPath(
                    "*",
                    await _loadPropertyDefinitions(fieldDefs, name),
                    remainingNames
                );
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
         * @param {string|Symbol} resModel
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
