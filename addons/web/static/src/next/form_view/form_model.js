import { signal } from "@odoo/owl";
import { Model } from "@web/model/model";
import { toCommands } from "../model/commands";
import { fieldFromDefinition } from "../model/fields";
import { Model as RecordModel } from "../model/model";
import { Store } from "../model/store";

/**
 * @typedef {{ [fieldName: string]: { fields?: Specification } }} Specification
 *  the `specification` of `web_read` and `web_save`
 */

/**
 * Loads one record into a record store, saves it back, and discards its
 * changes.
 *
 * The model does not keep field values itself: they live in the store, as
 * signals. Fields read them with `record.name()` and write them with
 * `record.name.set(value)`, and re-render when they change.
 *
 * The store belongs to this view: another view of the same record, with
 * another context or other fields, has its own.
 */
export class FormModel extends Model {
    /**
     * @param {{
     *  resModel: string;
     *  resId: number | false;
     *  specification: Specification;
     *  relatedModels: Record<string, { fields: Record<string, any> }>;
     *  context: Record<string, any>;
     * }} params
     */
    setup({ resModel, resId, specification, relatedModels, context }) {
        this.resModel = resModel;
        this.resId = resId;
        // binary fields come as their size, not as their content
        this.context = { ...context, bin_size: true };
        this.specification = specification;
        this.store = new Store({ models: buildModels(resModel, specification, relatedModels) });
        /** the displayed record, a record of the store */
        this.record = signal(null);
    }

    async load() {
        if (this.resId) {
            const [values] = await this.orm.webRead(this.resModel, [this.resId], {
                specification: this.specification,
                context: this.context,
            });
            this.record.set(this.store.load(this.resModel, values));
        } else {
            this.record.set(this.store.create(this.resModel));
        }
    }

    async save() {
        const record = this.record();
        const isNew = this.store.isNew(record);
        // `version` is the last change sent: edits made during the save stay dirty
        const { vals, version } = toCommands(record);
        const [values] = await this.orm.webSave(this.resModel, isNew ? [] : [record.id], vals, {
            specification: this.specification,
            context: this.context,
        });
        if (isNew) {
            this.store.rekey(record, values.id);
            this.resId = values.id;
        }
        this.store.ack(record, version);
        this.store.load(this.resModel, values);
    }

    /**
     * Drops the changes of the record. A record that was never saved is
     * replaced by a new empty one.
     */
    discard() {
        const record = this.record();
        const isNew = this.store.isNew(record);
        this.store.discard(record);
        if (isNew) {
            this.record.set(this.store.create(this.resModel));
        }
    }

    isDirty() {
        return this.store.isDirty(this.record());
    }
}

/**
 * The models of the store: the main one, and the comodels the specification
 * reaches, each with the fields the specification reads on it. No class
 * declares them in advance: their fields are the ones of the view. They are
 * editable, so that local changes are kept apart from the server values (that
 * is what `toCommands` sends).
 *
 * @param {string} resModel
 * @param {Specification} specification
 * @param {Record<string, { fields: Record<string, any> }>} relatedModels
 *  description of the fields of each model, from the view
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
 * @param {Record<string, { fields: Record<string, any> }>} relatedModels
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
