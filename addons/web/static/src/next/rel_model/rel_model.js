import { signal } from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";
import { Model } from "@web/model/model";
import { orderByToString } from "@web/search/utils/order_by";
import { toCommands } from "../store/commands";
import { Store } from "../store/store";
import { buildModels } from "../views/view_models";

/**
 * @typedef {import("../views/view_models").Specification} Specification
 * @typedef {import("../views/view_models").RelatedModels} RelatedModels
 */

/**
 * Loads the records of a view into a record store, and saves them back.
 *
 * A form view shows one record (`isMonoRecord`): the record of `resId`, or a
 * new one when there is none, as `record()`. A list view shows a page of the
 * records that match its search, as `records()`, out of `count()`.
 *
 * The model does not keep field values itself: they live in the store, as
 * signals. Fields read them with `record.name()` and write them with
 * `record.name.set(value)`, and re-render when they change.
 *
 * The store belongs to this view: another view of the same records, with
 * another context or other fields, has its own. Searches and pages load into
 * the same store.
 */
export class RelModel extends Model {
    /**
     * @param {{
     *  resModel: string;
     *  specification: Specification;
     *  relatedModels: RelatedModels;
     *  isMonoRecord?: boolean;
     *  resId?: number | false;
     *  limit?: number;
     * }} params
     */
    setup({
        resModel,
        specification,
        relatedModels,
        isMonoRecord = false,
        resId = false,
        limit = 80,
    }) {
        this.resModel = resModel;
        this.specification = specification;
        this.isMonoRecord = isMonoRecord;
        this.resId = resId;
        this.store = new Store({ models: buildModels(resModel, specification, relatedModels) });
        /** the record of a form view, a record of the store */
        this.record = signal(null);
        /** the records of the current page of a list view, records of the store */
        this.records = signal([]);
        /** number of records that match the search */
        this.count = signal(0);
        this.offset = signal(0);
        this.limit = signal(limit);
        this.searchParams = { domain: [], context: {}, orderBy: [] };
        // a search that comes back after a newer one is dropped
        this.keepLast = new KeepLast();
    }

    /**
     * Loads the record of a form view, or the first page of a search.
     *
     * @param {{ domain: any[]; context: Record<string, any>; orderBy: any[] }} searchParams
     */
    async load({ domain, context, orderBy }) {
        this.searchParams = { domain, context, orderBy };
        if (this.isMonoRecord) {
            await this.loadRecord();
        } else {
            await this.loadPage(0, this.limit());
        }
    }

    async loadRecord() {
        if (this.resId) {
            const [values] = await this.orm.webRead(this.resModel, [this.resId], {
                specification: this.specification,
                context: this.getContext(),
            });
            this.record.set(this.store.load(this.resModel, values));
        } else {
            this.record.set(this.store.create(this.resModel));
        }
    }

    /**
     * @param {number} offset
     * @param {number} limit
     */
    async loadPage(offset, limit) {
        const { domain, orderBy } = this.searchParams;
        const { length, records } = await this.keepLast.add(
            this.orm.webSearchRead(this.resModel, domain, {
                specification: this.specification,
                offset,
                limit,
                order: orderByToString(orderBy),
                context: this.getContext(),
            })
        );
        this.records.set(this.store.load(this.resModel, records));
        this.count.set(length);
        this.offset.set(offset);
        this.limit.set(limit);
    }

    /**
     * Saves the changes of a record of the store. A new record is created on
     * the server, and takes the id it gets.
     *
     * @param {any} record
     */
    async save(record) {
        const isNew = this.store.isNew(record);
        // `version` is the last change sent: edits made during the save stay dirty
        const { vals, version } = toCommands(record);
        const [values] = await this.orm.webSave(this.resModel, isNew ? [] : [record.id], vals, {
            specification: this.specification,
            context: this.getContext(),
        });
        if (isNew) {
            this.store.rekey(record, values.id);
            if (record === this.record()) {
                this.resId = values.id;
            }
        }
        this.store.ack(record, version);
        this.store.load(this.resModel, values);
    }

    /**
     * Drops the changes of a record of the store. The record of a form view
     * that was never saved is replaced by a new empty one.
     *
     * @param {any} record
     */
    discard(record) {
        const isNew = this.store.isNew(record);
        this.store.discard(record);
        if (isNew && record === this.record()) {
            this.record.set(this.store.create(this.resModel));
        }
    }

    /**
     * @param {any} record
     */
    isDirty(record) {
        return this.store.isDirty(record);
    }

    getContext() {
        // binary fields come as their size, not as their content
        return { ...this.searchParams.context, bin_size: true };
    }
}
