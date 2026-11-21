import { signal } from "@odoo/owl";
import { Model } from "@web/model/model";
import { toCommands } from "../model/commands";
import { fieldFromDefinition, fields as storeFields } from "../model/fields";
import { Model as RecordModel } from "../model/model";
import { Store } from "../model/store";

/**
 * Loads one record into a record store, saves it back, and discards its
 * changes.
 *
 * The model does not keep field values itself: they live in the store, as
 * signals. The renderer reads them with `record.name()` and writes them with
 * `record.name.set(value)`, and re-renders when they change.
 *
 * The store belongs to this view: another view of the same record, with
 * another context or other fields, has its own.
 */
export class SignalFormModel extends Model {
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
        this.store = new Store({ models: buildModels(resModel, fields, fieldNames) });
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
 * The models of the store: the main one with the fields of the arch, and each
 * comodel with its display name. No class declares them in advance: their
 * fields are the ones of the view. They are editable, so that local changes
 * are kept apart from the server values (that is what `toCommands` sends).
 *
 * @param {string} resModel
 * @param {Record<string, any>} fields description of the fields, from the view
 * @param {string[]} fieldNames
 */
function buildModels(resModel, fields, fieldNames) {
    /** @type {Record<string, Record<string, any>>} */
    const fieldsByModel = { [resModel]: {} };
    for (const name of fieldNames) {
        if (name === "id") {
            // records always have an id
            continue;
        }
        const { type, relation } = fields[name];
        fieldsByModel[resModel][name] = fieldFromDefinition({ type, relation });
        if (relation) {
            fieldsByModel[relation] ||= {};
            fieldsByModel[relation].display_name ||= storeFields.Char();
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
