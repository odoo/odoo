/* @odoo-module */

import { DataPoint } from "./datapoint";

export class StaticList extends DataPoint {
    setup(params) {
        this._parent = params.parent;
        this.orderBy = params.orderBy || [];
        this.limit = params.limit || 40;
        this.offset = params.offset || 0;
        this.resIds = params.data.map((r) => r.id);
        this.records = params.data.slice(this.offset, this.limit).map(
            (r) =>
                new this.model.constructor.Record(this.model, {
                    context: this.context,
                    activeFields: this.activeFields,
                    resModel: this.resModel,
                    fields: this.fields,
                    data: r,
                    parentRecord: this._parent,
                })
        );
        this.count = this.resIds.length;
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get currentIds() {
        return this.records.map((r) => r.resId);
    }

    get evalContext() {
        return {
            parent: this._parent.evalContext,
        };
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    canResequence() {
        return false;
    }
}
StaticList.DEFAULT_LIMIT = 40;
