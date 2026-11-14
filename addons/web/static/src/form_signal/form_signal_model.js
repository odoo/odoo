import { signal } from "@odoo/owl";
import { Model } from "@web/model/model";
import { toCommands } from "./model/commands";
import { Model as StoreModel } from "./model/model";
import { RecordStore } from "./model/store";

/**
 * Loads one record into a record store, and saves it back.
 *
 * The model does not keep field values itself: they live in the store, as
 * signals. The renderer reads them with `record.name()` and writes them with
 * `record.name.set(value)`, and re-renders when they change.
 */
export class FormSignalModel extends Model {
    /**
     * @param {{
     *  resModel: string;
     *  resId: number | false;
     *  fields: Record<string, any>;
     *  fieldNames: string[];
     *  context: Record<string, any>;
     * }} params
     */
    setup({ resModel, resId, fields, fieldNames, context }) {
        this.resModel = resModel;
        this.resId = resId;
        // binary fields come as their size, not as their content
        this.context = { ...context, bin_size: true };
        this.specification = buildSpecification(fields, fieldNames);
        this.store = new RecordStore(buildStoreParams(resModel, fields, fieldNames));
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

    isDirty() {
        return this.store.isDirty(this.record());
    }
}

/**
 * The `specification` of `web_read` and `web_save`: the fields of the arch,
 * with the display name of related records.
 *
 * @param {Record<string, any>} fields
 * @param {string[]} fieldNames
 */
function buildSpecification(fields, fieldNames) {
    const specification = {};
    for (const name of fieldNames) {
        specification[name] = fields[name].relation ? { fields: { display_name: {} } } : {};
    }
    return specification;
}

/**
 * The store knows the main model with the fields of the arch, and each
 * comodel with its display name. Models are tracked, so that local changes are
 * kept apart from the server values (that is what `toCommands` sends).
 *
 * @param {string} resModel
 * @param {Record<string, any>} fields
 * @param {string[]} fieldNames
 */
function buildStoreParams(resModel, fields, fieldNames) {
    const definitions = { [resModel]: { fields: {} } };
    for (const name of fieldNames) {
        const { type, string, relation } = fields[name];
        definitions[resModel].fields[name] = { type, string, relation };
        if (relation) {
            definitions[relation] ||= { fields: {} };
            definitions[relation].fields.display_name ||= { type: "char" };
        }
    }
    const models = Object.keys(definitions).map(
        (name) =>
            class extends StoreModel {
                static _name = name;
                static _tracked = true;
            }
    );
    return { models, definitions };
}
