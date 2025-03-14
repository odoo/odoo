import { Domain } from "@web/core/domain";
import { registry } from "@web/core/registry";

/**
 * @typedef {Object} LoadFieldsOptions
 * @property {string[]|false} [fieldNames]
 * @property {string[]} [attributes]
 */

function getRelation(fieldDef, followRelationalProperties = false) {
    if (fieldDef.relation) {
        return fieldDef.relation;
    }
    if (fieldDef.comodel && followRelationalProperties) {
        return fieldDef.comodel;
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
            if (typeof resModel !== "string" || !resModel) {
                throw new Error(`Invalid model name: ${resModel}`);
            }
            return orm
                .cached()
                .call(resModel, "fields_get", [options.fieldNames, options.attributes]);
        }

        /**
         * @param {Object} fieldDefs
         * @param {string} name
         * @param {import("@web/core/domain").DomainListRepr} [domain=[]]
         * @returns {Promise<Object>}
         */
        async function _loadPropertyDefinitions(resModel, fieldDefs, name, domain = []) {
            const {
                definition_record: definitionRecord,
                definition_record_field: definitionRecordField,
            } = fieldDefs[name];
            const definitionRecordModel = fieldDefs[definitionRecord].relation;

            let result;
            if (definitionRecordModel === "properties.base.definition") {
                // Record without parent (eg `res.partner`)
                result = await orm.call(
                    "properties.base.definition",
                    "get_properties_base_definition",
                    [resModel, name]
                );
            } else {
                // @ts-ignore
                domain = Domain.and([[[definitionRecordField, "!=", false]], domain]).toList();
                result = await orm.webSearchRead(definitionRecordModel, domain, {
                    specification: {
                        display_name: {},
                        [definitionRecordField]: {},
                    },
                });
            }

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
            return _loadPropertyDefinitions(resModel, fieldDefs, fieldName, domain);
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
                    await _loadPropertyDefinitions(resModel, fieldDefs, name),
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
