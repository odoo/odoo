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
    }
}
DynamicRecordList.WEB_SEARCH_READ_COUNT_LIMIT = 10000; // FIXME: move
