/* @odoo-module */

import { KeepLast } from "@web/core/utils/concurrency";
import { Model } from "@web/views/helpers/model";

class DataPoint {
    static nextId = 1;

    constructor(model) {
        this.id = DataRecord.nextId++;
        this.model = model;
        this.fields = model.fields;
        this.orm = model.orm;
        model.db[this.id] = this;
    }
}

class DataRecord extends DataPoint {
    /**
     *
     * @param {RelationalModel} model
     * @param {number} resId
     */
    constructor(model, resId, data) {
        super(model);
        this.resId = resId;
        this.data = data || {};
    }

    async load() {
        const fields = this.model.activeFields;
        const records = await this.orm.read(this.model.resModel, [this.resId], fields);
        this.data = records[0];
    }
}

class DataList extends DataPoint {
    data = [];

    async load(params) {
        this.domain = params.domain;
        const fields = this.model.activeFields;
        const rawRecords = await this.orm.searchRead(this.model.resModel, this.domain, fields, {
            limit: 40
        });
        this.data = rawRecords.map((record) => new DataRecord(this.model, record.id, record));
    }
}

export class RelationalModel extends Model {
    static services = ["orm"];

    setup(params, { orm }) {
        window.basicmodel = this; // debug
        this.db = Object.create(null);
        this.resModel = params.resModel;
        this.resId = params.resId;
        this.resIds = params.resIds;
        this.fields = params.fields;
        this.activeFields = params.activeFields;

        this.orm = orm;
        this.keepLast = new KeepLast();
        this.type = this.resId ? "record" : "list";

        // if (this.resId) {
        //     // in datarecord mode (form view)
        //     this.root = new DataRecord(this, this.resId);
        // } else {
        //     // datalist mode (list/kanban/...)
        //     this.root = new DataList(this);
        // }
    }

    async load(params) {
        if (this.type === "record") {
            await this.loadRecord();
        } else if (this.type === "list") {
            await this.loadCollection(params);
        }
    }

    async loadRecord(params = {}) {
        this.resId = params.resId || this.resId;
        this.root = new DataRecord(this, this.resId);
        await this.keepLast.add(this.root.load());
        this.notify();
    }

    async loadCollection(params) {
        this.root = new DataList(this);
        await this.keepLast.add(this.root.load(params));
        this.notify();
    }
}
