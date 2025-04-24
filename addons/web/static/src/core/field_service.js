import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { deepCopy } from "@web/core/utils/objects";

/**
 * @typedef {Object} LoadFieldsOptions
 * @property {string[]|false} [fieldNames]
 * @property {string[]} [attributes]
 */

const MODEL_DATE_PROPERTIES = "__model__date_properties__";
const DATE_PROPERTIES = Object.fromEntries(
    Object.entries({
        day_of_week: { string: _t("Weekday") },
        day_of_month: { string: _t("Day of month") },
        day_of_year: { string: _t("Day of year") },
        iso_week_number: { string: _t("Week number") },
        month_number: { string: _t("Month") },
        quarter_number: { string: _t("Quarter") },
        year_number: { string: _t("Year") },
    }).map(([name, o]) => [name, { ...o, searchable: true, name, type: "date_option" }])
);

const MODEL_TIME_PROPERTIES = "__model__time_properties__";
const TIME_PROPERTIES = Object.fromEntries(
    Object.entries({
        hour_number: { string: _t("Hour") },
        minute_number: { string: _t("Minute") },
        second_number: { string: _t("Second") },
    }).map(([name, o]) => [name, { ...o, searchable: true, name, type: "time_option" }])
);

const MODEL_DATETIME_PROPERTIES = "__model__datetime_properties__";
const DATETIME_PROPERTIES = Object.fromEntries(
    Object.entries({
        __date: { string: _t("Date"), relation: MODEL_DATE_PROPERTIES }, // virtual: defined via year_number, month_number, and day_of_month
        __time: { string: _t("Time"), relation: MODEL_TIME_PROPERTIES }, // virtual: defined via hour_number, minute_number, and second_number
    }).map(([name, o]) => [name, { ...o, searchable: true, name, type: "datetime_option" }])
);

export const SPECIAL_MODEL_NAMES = new Set([
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

function getRelation(fieldDef, followRelationalProperties = false) {
    if (fieldDef.relation) {
        return fieldDef.relation;
    }
    if (fieldDef.comodel && followRelationalProperties) {
        return fieldDef.comodel;
    }
    if (fieldDef.type === "datetime") {
        return MODEL_DATETIME_PROPERTIES;
    }
    if (fieldDef.type === "date") {
        return MODEL_DATE_PROPERTIES;
    }
    return null;
}

export const fieldService = {
    dependencies: ["orm"],
    async: ["loadFields", "loadPath", "loadPropertyDefinitions"],
    start(env, { orm }) {
        /**
         * @param {string} resModel
         * @param {LoadFieldsOptions} [options]
         * @returns {Promise<object>}
         */
        async function loadFields(resModel, options = {}) {
            if (SPECIAL_MODEL_NAMES.has(resModel)) {
                return getSpecialModelFields(resModel);
            }
            if (typeof resModel !== "string" || !resModel) {
                throw new Error(`Invalid model name: ${resModel}`);
            }
            return orm.cached.call(resModel, "fields_get", [
                options.fieldNames,
                options.attributes,
            ]);
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
                        ...(definition.comodel ? { relation: definition.comodel } : {}),
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
         * @param {boolean} [followRelationalProperties=false]
         */
        async function _loadPath(resModel, fieldDefs, names, followRelationalProperties = false) {
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
            const relation = getRelation(fieldDef, followRelationalProperties);
            if (relation) {
                subResult = await _loadPath(relation, await loadFields(relation), remainingNames);
            } else if (fieldDef.type === "properties") {
                subResult = await _loadPath(
                    followRelationalProperties ? resModel : "*",
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
         * @param {string} resModel
         * @param {string} path
         * @returns {Promise<Object>}
         */
        async function loadPath(resModel, path = "*", followRelationalProperties = false) {
            const fieldDefs = await loadFields(resModel);
            if (typeof path !== "string" || !path) {
                throw new Error(`Invalid path: ${path}`);
            }
            return _loadPath(resModel, fieldDefs, path.split("."), followRelationalProperties);
        }

        return { loadFields, loadPath, loadPropertyDefinitions };
    },
};

registry.category("services").add("field", fieldService);
