import { fieldFromDefinition } from "../store/fields";
import { Model as RecordModel } from "../store/model";

/**
 * @typedef {{ [fieldName: string]: { fields?: Specification } }} Specification
 *  the `specification` of `web_read`, `web_search_read` and `web_save`
 *
 * @typedef {Record<string, { fields: Record<string, any> }>} RelatedModels
 *  description of the fields of each model, from the view
 */

/**
 * The models of the store: the main one, and the comodels the specification
 * reaches, each with the fields the specification reads on it. No class
 * declares them in advance: their fields are the ones of the view. They are
 * editable, so that local changes are kept apart from the server values (that
 * is what `toCommands` sends).
 *
 * @param {string} resModel
 * @param {Specification} specification
 * @param {RelatedModels} relatedModels
 */
export function buildModels(resModel, specification, relatedModels) {
    /** @type {Record<string, Record<string, any>>} */
    const fieldsByModel = {};

    /**
     * @param {string} modelName
     * @param {Specification} spec
     */
    const visit = (modelName, spec) => {
        fieldsByModel[modelName] ||= {};
        for (const [name, subSpec] of Object.entries(spec)) {
            if (name === "id") {
                // records always have an id
                continue;
            }
            const definition = getDefinition(relatedModels, modelName, name);
            fieldsByModel[modelName][name] ||= fieldFromDefinition(definition);
            if (definition.relation) {
                visit(definition.relation, subSpec.fields || {});
            }
        }
    };
    visit(resModel, specification);

    // an inverse the view does not read is not a field of the store
    for (const modelFields of Object.values(fieldsByModel)) {
        for (const declaration of Object.values(modelFields)) {
            if (declaration.inverse && !fieldsByModel[declaration.relation][declaration.inverse]) {
                delete declaration.inverse;
            }
        }
    }

    return Object.entries(fieldsByModel).map(
        ([name, modelFields]) =>
            class extends RecordModel {
                static _name = name;
                static _editable = true;
                static fields = modelFields;
            }
    );
}

/**
 * @param {RelatedModels} relatedModels
 * @param {string} modelName
 * @param {string} fieldName
 */
function getDefinition(relatedModels, modelName, fieldName) {
    const definition = relatedModels[modelName]?.fields[fieldName];
    if (definition) {
        return definition;
    }
    if (fieldName === "display_name") {
        // read on every comodel, but not always part of its description
        return { type: "char" };
    }
    throw new Error(`Unknown field "${modelName}.${fieldName}"`);
}
