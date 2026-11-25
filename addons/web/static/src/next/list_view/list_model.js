import { signal } from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";
import { Model } from "@web/model/model";
import { orderByToString } from "@web/search/utils/order_by";
import { Store } from "../model/store";
import { buildModels } from "../views/view_models";

/**
 * @typedef {import("../views/view_models").Specification} Specification
 * @typedef {import("../views/view_models").RelatedModels} RelatedModels
 */

/**
 * Loads a page of the records that match a search into a record store.
 *
 * Like the form model, it does not keep field values: they live in the store,
 * as signals. Pages and searches load into the same store.
 */
export class ListModel extends Model {
    /**
     * @param {{
     *  resModel: string;
     *  specification: Specification;
     *  relatedModels: RelatedModels;
     *  limit: number;
     * }} params
     */
    setup({ resModel, specification, relatedModels, limit }) {
        this.resModel = resModel;
        this.specification = specification;
        this.store = new Store({ models: buildModels(resModel, specification, relatedModels) });
        /** the records of the current page, records of the store */
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
     * Loads the first page of a search.
     *
     * @param {{ domain: any[]; context: Record<string, any>; orderBy: any[] }} searchParams
     */
    async load({ domain, context, orderBy }) {
        this.searchParams = { domain, context, orderBy };
        await this.loadPage(0, this.limit());
    }

    /**
     * @param {number} offset
     * @param {number} limit
     */
    async loadPage(offset, limit) {
        const { domain, context, orderBy } = this.searchParams;
        const { length, records } = await this.keepLast.add(
            this.orm.webSearchRead(this.resModel, domain, {
                specification: this.specification,
                offset,
                limit,
                order: orderByToString(orderBy),
                // binary fields come as their size, not as their content
                context: { ...context, bin_size: true },
            })
        );
        this.records.set(this.store.load(this.resModel, records));
        this.count.set(length);
        this.offset.set(offset);
        this.limit.set(limit);
    }
}
