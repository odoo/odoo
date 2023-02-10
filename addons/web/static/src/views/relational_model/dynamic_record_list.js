/* @odoo-module */

import { DynamicList } from "./dynamic_list";
import { getFieldsSpec } from "./utils";

export class DynamicRecordList extends DynamicList {
    setup(params) {
        super.setup(params);
        this.records = params.data.records.map(
            (r) =>
                new this.model.constructor.Record(this.model, {
                    activeFields: this.activeFields,
                    fields: this.fields,
                    resModel: this.resModel,
                    context: this.context,
                    resIds: params.data.records.map((r) => r.id),
                    data: r,
                })
        );
        this.hasLimitedCount = false;
        this._updateCount(params.data);
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * Performs a search_count with the current domain to set the count. This is
     * useful as web_search_read limits the count for performance reasons, so it
     * might sometimes be less than the real number of records matching the domain.
     **/
    async fetchCount() {
        const keepLast = this.model.keepLast;
        this.count = await keepLast.add(this.model.orm.searchCount(this.resModel, this.domain));
        this.hasLimitedCount = false;
        return this.count;
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    _updateCount(data) {
        const length = data.length;
        if (length === this.constructor.WEB_SEARCH_READ_COUNT_LIMIT + 1) {
            this.hasLimitedCount = true;
            this.count = length - 1;
        } else {
            this.hasLimitedCount = false;
            this.count = length;
        }
    }

    async _load() {
        const fieldSpec = getFieldsSpec(this.activeFields, this.fields);
        console.log("Unity field spec", fieldSpec);
        const kwargs = {
            fields: fieldSpec,
            domain: this.domain,
            offset: this.offset,
            limit: this.limit,
            context: { bin_size: true, ...this.context },
        };
        const response = await this.model.orm.call(
            this.resModel,
            "web_search_read_unity",
            [],
            kwargs
        );
        console.log("Unity response", response);
        this.records = response.records.map(
            (r) =>
                new this.model.constructor.Record(this.model, {
                    activeFields: this.activeFields,
                    fields: this.fields,
                    resModel: this.resModel,
                    context: this.context,
                    resIds: response[0].records.map((r) => r.id),
                    data: r,
                })
        );
        this._updateCount(response);
    }
}
DynamicRecordList.WEB_SEARCH_READ_COUNT_LIMIT = 10000; // FIXME: move
