// @ts-check
/** @odoo-module native */

/**
 * @typedef {Object} LoadFieldsOptions
 * @property {string[]|false} [fieldNames]
 * @property {string[]} [attributes]
 */

/**
 * @typedef {Object} LoadPathResult
 * @property {string} [isInvalid]
 * @property {string[]} names
 * @property {{ resModel: string | null, fieldDefs: any }[]} modelsInfo
 */

import { Domain } from "@web/core/domain";
import { registry } from "@web/core/registry";

/**
 * @typedef {Object} PropertyDefinitionRecord
 * @property {number} definitionRecordId
 * @property {string} definitionRecordName
 * @property {Record<string, any>[]} definitions
 */

/**
 * Field paths identify properties by name, whereas search filters also need the
 * definition record. Preserve the historical last-name-wins path index here.
 * @param {PropertyDefinitionRecord[]} records
 * @returns {Record<string, any>}
 */
function indexPropertyDefinitions(records) {
    const definitions = Object.create(null);
    for (const record of records) {
        for (const definition of record.definitions) {
            definitions[definition.name] = definition;
        }
    }
    return definitions;
}

const BASE_DEFINITION_MODEL = "properties.base.definition";
const BASE_DEFINITION_FIELD = "properties_definition";

/**
 * @param {Record<string, any> | null | undefined} fieldDefs
 * @param {string} name
 * @returns {Record<string, any> | undefined}
 */
function getOwnFieldDef(fieldDefs, name) {
    return fieldDefs && Object.hasOwn(fieldDefs, name) ? fieldDefs[name] : undefined;
}

/**
 * @param {Record<string, any>} fieldDef
 * @param {boolean} [followRelationalProperties=false]
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

class FieldService {
    /** @param {{ orm: any }} services */
    constructor({ orm }) {
        this.orm = orm;
    }

    /**
     * @param {string} resModel
     * @param {LoadFieldsOptions} [options]
     * @returns {Promise<Record<string, Readonly<Record<string, any>>>>}
     */
    async loadFields(resModel, options = {}) {
        if (typeof resModel !== "string" || !resModel) {
            throw new Error(`Invalid model name: ${resModel}`);
        }
        const fields = await this.orm
            .cache({ type: "disk", immutable: true })
            .retry(1)
            .call(resModel, "fields_get", [options.fieldNames, options.attributes]);
        return { ...fields };
    }

    /**
     * @param {string} resModel
     * @param {Record<string, any>} fieldDefs
     * @param {string} name
     * @param {import("@web/core/domain").DomainListRepr} [domain=[]]
     * @returns {Promise<PropertyDefinitionRecord[]>}
     */
    async _loadPropertyDefinitionsByRecord(resModel, fieldDefs, name, domain = []) {
        const fieldDef = getOwnFieldDef(fieldDefs, name);
        if (!fieldDef) {
            throw new Error(`Model "${resModel}" has no field "${name}"`);
        }
        const {
            definition_record: definitionRecord,
            definition_record_field: definitionRecordField,
        } = fieldDef;
        const definitionRecordDef = getOwnFieldDef(fieldDefs, definitionRecord);
        if (!definitionRecordField || !definitionRecordDef) {
            throw new Error(
                `Field "${resModel}.${name}" is not a properties field ` +
                    `(no definition record to read its definitions from)`,
            );
        }
        const definitionRecordModel = definitionRecordDef.relation;

        let result;
        if (definitionRecordModel === BASE_DEFINITION_MODEL) {
            if (definitionRecordField !== BASE_DEFINITION_FIELD) {
                throw new Error(
                    `Field "${resModel}.${name}" names ` +
                        `"${definitionRecordField}" as its definition_record_field, ` +
                        `but ${BASE_DEFINITION_MODEL} only serves ` +
                        `"${BASE_DEFINITION_FIELD}"`,
                );
            }
            result = await this.orm
                .retry(1)
                .call(BASE_DEFINITION_MODEL, "get_properties_base_definition", [
                    resModel,
                    name,
                ]);
        } else {
            // @ts-ignore
            domain = Domain.and([
                [[definitionRecordField, "!=", false]],
                domain,
            ]).toList();
            result = await this.orm.webSearchRead(definitionRecordModel, domain, {
                specification: {
                    display_name: {},
                    [definitionRecordField]: {},
                },
            });
        }

        return result.records.map((record) => ({
            definitionRecordId: record.id,
            definitionRecordName: record.display_name,
            definitions: record[definitionRecordField].map((definition) => ({
                is_property: true,
                searchable: true,
                record_id: record.id,
                record_name: record.display_name,
                ...(definition.comodel ? { relation: definition.comodel } : {}),
                ...definition,
            })),
        }));
    }

    /**
     * @param {string} resModel
     * @param {string} fieldName
     * @param {import("@web/core/domain").DomainListRepr} [domain]
     * @returns {Promise<Record<string, any>>}
     */
    async loadPropertyDefinitions(resModel, fieldName, domain) {
        return indexPropertyDefinitions(
            await this.loadPropertyDefinitionsByRecord(resModel, fieldName, domain),
        );
    }

    /**
     * @param {string} resModel
     * @param {string} fieldName
     * @param {import("@web/core/domain").DomainListRepr} [domain]
     * @returns {Promise<PropertyDefinitionRecord[]>}
     */
    async loadPropertyDefinitionsByRecord(resModel, fieldName, domain) {
        const fieldDefs = await this.loadFields(resModel);
        return this._loadPropertyDefinitionsByRecord(
            resModel,
            fieldDefs,
            fieldName,
            domain,
        );
    }

    /**
     * @param {string|null} resModel
     * @param {Record<string, any>|null} fieldDefs
     * @param {string[]} names
     * @param {boolean} [followRelationalProperties=false]
     * @returns {Promise<LoadPathResult>}
     */
    async _loadPath(resModel, fieldDefs, names, followRelationalProperties = false) {
        if (!fieldDefs) {
            return { isInvalid: "path", names, modelsInfo: [] };
        }

        const [name, ...remainingNames] = names;
        const modelsInfo = [{ resModel, fieldDefs }];
        if (resModel === "*" && remainingNames.length) {
            return { isInvalid: "path", names, modelsInfo };
        }

        const fieldDef = getOwnFieldDef(fieldDefs, name);
        if (name === "*") {
            return remainingNames.length
                ? { isInvalid: "path", names, modelsInfo }
                : { names, modelsInfo };
        }
        if (!fieldDef) {
            return { isInvalid: "path", names, modelsInfo };
        }

        if (!remainingNames.length) {
            return { names, modelsInfo };
        }

        let subResult;
        const relation = getRelation(fieldDef, followRelationalProperties);
        if (relation) {
            subResult = await this._loadPath(
                relation,
                await this.loadFields(relation),
                remainingNames,
                followRelationalProperties,
            );
        } else if (fieldDef.type === "properties") {
            subResult = await this._loadPath(
                followRelationalProperties ? resModel : "*",
                indexPropertyDefinitions(
                    await this._loadPropertyDefinitionsByRecord(
                        /** @type {string} */ (resModel),
                        fieldDefs,
                        name,
                    ),
                ),
                remainingNames,
                followRelationalProperties,
            );
        }

        if (subResult) {
            /** @type {LoadPathResult} */
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
     * @param {string} resModel
     * @param {string} path
     * @returns {Promise<LoadPathResult>}
     */
    async loadPath(resModel, path = "*", followRelationalProperties = false) {
        if (typeof path !== "string" || !path) {
            throw new Error(`Invalid path: ${path}`);
        }
        const fieldDefs = await this.loadFields(resModel);
        return this._loadPath(
            resModel,
            fieldDefs,
            path.split("."),
            followRelationalProperties,
        );
    }

    /**
     * @param {string} resModel
     * @param {string} path
     * @returns {Promise<Object>}
     */
    async loadFieldInfo(resModel, path) {
        if (typeof path !== "string" || !path || path === "*") {
            return { resModel, fieldDef: null };
        }
        const { isInvalid, names, modelsInfo } = await this.loadPath(resModel, path);
        if (isInvalid) {
            return { resModel, fieldDef: null };
        }
        const name = names[names.length - 1];
        const modelInfo = modelsInfo[modelsInfo.length - 1];
        return {
            resModel: modelInfo.resModel,
            fieldDef: getOwnFieldDef(modelInfo.fieldDefs, name) ?? null,
        };
    }

    /** @param {any} [value] */
    makeString(value) {
        return String(value ?? "-");
    }

    /**
     * @param {string} resModel
     * @param {string | number} path
     * @param {boolean} [allowEmpty]
     * @returns {Promise<{ isInvalid: boolean, displayNames: string[] }>}
     */
    async loadPathDescription(resModel, path, allowEmpty) {
        if ([0, 1].includes(/** @type {number} */ (path))) {
            return { isInvalid: false, displayNames: [this.makeString(path)] };
        }
        if (allowEmpty && !path) {
            return { isInvalid: false, displayNames: [] };
        }
        if (typeof path !== "string" || !path || path === "*") {
            return { isInvalid: true, displayNames: [this.makeString()] };
        }
        const { isInvalid, modelsInfo, names } = await this.loadPath(resModel, path);
        const result = {
            isInvalid: !!isInvalid,
            displayNames: /** @type {string[]} */ ([]),
        };
        if (!isInvalid) {
            const lastName = names[names.length - 1];
            const lastFieldDef = getOwnFieldDef(
                modelsInfo[modelsInfo.length - 1].fieldDefs,
                lastName,
            );
            if (
                !lastFieldDef ||
                ["properties", "properties_definition"].includes(lastFieldDef.type)
            ) {
                result.isInvalid = true;
            }
        }
        for (let index = 0; index < names.length; index++) {
            const name = names[index];
            const fieldDef = getOwnFieldDef(modelsInfo[index]?.fieldDefs, name);
            result.displayNames.push(fieldDef?.string || this.makeString(name));
        }
        return result;
    }
}

export const fieldService = {
    dependencies: ["orm"],
    async: [
        "loadFieldInfo",
        "loadFields",
        "loadPath",
        "loadPropertyDefinitions",
        "loadPropertyDefinitionsByRecord",
        "loadPathDescription",
    ],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{ orm: any }} services
     * @returns {FieldService}
     */
    start(env, services) {
        return new FieldService(services);
    },
};

registry.category("services").add("field", fieldService);
