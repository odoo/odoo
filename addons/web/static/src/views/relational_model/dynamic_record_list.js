/* @odoo-module */

import { DynamicList } from "./dynamic_list";

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

    load(params = {}) {
        const limit = params.limit === undefined ? this.limit : params.limit;
        const offset = params.offset === undefined ? this.offset : params.offset;
        return this.model.mutex.exec(() => this._load(offset, limit));
    }

    deleteRecords(records) {
        return this.model.mutex.exec(async () => {
            const unlinked = await this.model.orm.unlink(
                this.resModel,
                records.map((r) => r.resId),
                {
                    context: this.context,
                }
            );
            if (!unlinked) {
                return false;
            }
            return this._removeRecords(records);
        });
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    _removeRecords(records) {
        const _records = this.records.filter((r) => !records.includes(r));
        if (this.offset && !_records.length) {
            const offset = Math.max(this.offset - this.limit, 0);
            return this._load(offset, this.limit);
        }
        this.records = _records;
        this._updateCount(this.records);
    }

    _updateCount(data) {
        const length = data.length;
        if (length >= this.model.countLimit + 1) {
            this.hasLimitedCount = true;
            this.count = this.model.countLimit;
        } else {
            this.hasLimitedCount = false;
            this.count = length;
        }
    }

    async _load(offset, limit) {
        const response = await this.model._loadUngroupedList({
            activeFields: this.activeFields,
            context: this.context,
            domain: this.domain,
            fields: this.fields,
            limit,
            offset,
            resModel: this.resModel,
        });
        this.records = response.records.map(
            (r) =>
                new this.model.constructor.Record(this.model, {
                    activeFields: this.activeFields,
                    fields: this.fields,
                    resModel: this.resModel,
                    context: this.context,
                    resIds: response.records.map((r) => r.id),
                    data: r,
                })
        );
        this.offset = offset;
        this.limit = limit;
        this._updateCount(response);
    }
}
