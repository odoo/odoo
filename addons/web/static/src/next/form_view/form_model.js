import { signal } from "@odoo/owl";
import { Model } from "@web/model/model";
import { toCommands } from "../model/commands";
import { Store } from "../model/store";
import { buildModels } from "../views/view_models";

/**
 * @typedef {import("../views/view_models").Specification} Specification
 * @typedef {import("../views/view_models").RelatedModels} RelatedModels
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
     *  relatedModels: RelatedModels;
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
