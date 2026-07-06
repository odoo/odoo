import { Domain } from "@web/core/domain";
import { registry } from "@web/core/registry";
import { plugin, Plugin } from "@odoo/owl";
import { services } from "@web/core/services";
import { ORM } from "@web/core/orm_plugin";

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

function makeString(value) {
    return String(value ?? "-");
}

export class FieldPlugin extends Plugin {
    orm = plugin(ORM);

    /**
     * @param {string} resModel
     * @param {LoadFieldsOptions} [options]
     * @returns {Promise<object>}
     */
    async loadFields(resModel, options = {}) {
        if (typeof resModel !== "string" || !resModel) {
            throw new Error(`Invalid model name: ${resModel}`);
        }
        return this.orm
            .cache({ type: "disk" })
            .call(resModel, "fields_get", [options.fieldNames, options.attributes]);
    }

    /**
     * @param {Object} fieldDefs
     * @param {string} name
     * @param {import("@web/core/domain").DomainListRepr} [domain=[]]
     * @returns {Promise<Object>}
     */
    async _loadPropertyDefinitions(resModel, fieldDefs, name, domain = []) {
        const {
            definition_record: definitionRecord,
            definition_record_field: definitionRecordField,
        } = fieldDefs[name];
        const definitionRecordModel = fieldDefs[definitionRecord].relation;

        let result;
        if (definitionRecordModel === "properties.base.definition") {
            // Record without parent (eg `res.partner`)
            result = await this.orm.call(
                "properties.base.definition",
                "get_properties_base_definition",
                [resModel, name]
            );
        } else {
            // @ts-ignore
            domain = Domain.and([[[definitionRecordField, "!=", false]], domain]).toList();
            result = await this.orm.webSearchRead(definitionRecordModel, domain, {
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
    async loadPropertyDefinitions(resModel, fieldName, domain) {
        const fieldDefs = await this.loadFields(resModel);
        return this._loadPropertyDefinitions(resModel, fieldDefs, fieldName, domain);
    }

    /**
     * @param {string|null} resModel valid model name or null (case virtual)
     * @param {Object|null} fieldDefs
     * @param {string[]} names
     * @param {boolean} [followRelationalProperties=false]
     * @private
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
            subResult = await this._loadPath(relation, await this.loadFields(relation), remainingNames);
        } else if (fieldDef.type === "properties") {
            subResult = await this._loadPath(
                followRelationalProperties ? resModel : "*",
                await this._loadPropertyDefinitions(resModel, fieldDefs, name),
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
    async loadPath(resModel, path = "*", followRelationalProperties = false) {
        const fieldDefs = await this.loadFields(resModel);
        if (typeof path !== "string" || !path) {
            throw new Error(`Invalid path: ${path}`);
        }
        return this._loadPath(resModel, fieldDefs, path.split("."), followRelationalProperties);
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
        const name = names.at(-1);
        const modelInfo = modelsInfo.at(-1);
        return { resModel: modelInfo.resModel, fieldDef: modelInfo.fieldDefs[name] };
    }

    async loadPathDescription(resModel, path, allowEmpty) {
        if ([0, 1].includes(path)) {
            return { isInvalid: false, displayNames: [makeString(path)] };
        }
        if (allowEmpty && !path) {
            return { isInvalid: false, displayNames: [] };
        }
        if (typeof path !== "string" || !path || path === "*") {
            return { isInvalid: true, displayNames: [makeString()] };
        }
        const { isInvalid, modelsInfo, names } = await this.loadPath(resModel, path);
        const result = { isInvalid: !!isInvalid, displayNames: [] };
        if (!isInvalid) {
            const lastName = names.at(-1);
            const lastFieldDef = modelsInfo.at(-1).fieldDefs[lastName];
            if (["properties", "properties_definition"].includes(lastFieldDef.type)) {
                // there is no known case where we want to select a 'properties' field directly
                result.isInvalid = true;
            }
        }
        for (let index = 0; index < names.length; index++) {
            const name = names[index];
            const fieldDef = modelsInfo[index]?.fieldDefs[name];
            result.displayNames.push(fieldDef?.string || makeString(name));
        }
        return result;
    }
}

services.add(FieldPlugin);

/**
 * @todo owl3 migration
 * temporary - to remove when all use of field services are removed
 */
registry.category("services").add("field", {
    async: [
        "loadFieldInfo",
        "loadFields",
        "loadPath",
        "loadPropertyDefinitions",
        "loadPathDescription",
    ],
    start() {
        return plugin(FieldPlugin);
    },
});
