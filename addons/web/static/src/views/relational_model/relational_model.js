/* @odoo-module */

import { EventBus, markRaw } from "@odoo/owl";
import { KeepLast, Mutex } from "@web/core/utils/concurrency";
import { unique } from "@web/core/utils/arrays";
import { Model } from "@web/views/model";
import { orderByToString } from "@web/views/utils";
import { Record } from "./record";
import { DynamicRecordList } from "./dynamic_record_list";
import { DynamicGroupList } from "./dynamic_group_list";
import { Group } from "./group";
import { StaticList } from "./static_list";
import { getFieldsSpec } from "./utils";

export class RelationalModel extends Model {
    // FIXME: ask sad :D without this, can't make instance of model reactive.
    // EventTarget might be added to the list of supported types in SUPPORTED_RAW_TYPES (owl)
    get [Symbol.toStringTag]() {
        return "Object";
    }

    setup(params, { user, company, notification }) {
        this.user = user;
        this.company = company;
        this.notificationService = notification;

        this.bus = new EventBus();

        this.keepLast = markRaw(new KeepLast());
        this.mutex = markRaw(new Mutex());

        console.log("coucou");
        this.rootParams = markRaw(params);
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    hasData() {
        return this.rootParams.viewMode !== "form" ? this.root.count > 0 : true;
    }
    /**
     * @param {Object} [params={}]
     * @param {Comparison | null} [params.comparison]
     * @param {Context} [params.context]
     * @param {DomainListRepr} [params.domain]
     * @param {string[]} [params.groupBy]
     * @param {Object[]} [params.orderBy]
     * @param {number} [params.resId] should not be there
     * @returns {Promise<void>}
     */
    async load(params = {}) {
        // rootParams must be changed directly, because we could get multiple
        // load requests, with different params, and they must be aggregated
        // is it really true? to check
        Object.assign(this.rootParams, params);
        // only one level of groups in kanban (FIXME: do it differently?)
        if (this.rootParams.viewMode === "kanban") {
            this.rootParams.groupBy = this.rootParams.groupBy.slice(0, 1);
        }
        // apply default groupBy and orderBy
        if (
            this.rootParams.defaultGroupBy &&
            !this.env.inDialog &&
            !this.rootParams.groupBy.length
        ) {
            this.rootParams.groupBy = [this.rootParams.defaultGroupBy];
        }
        // if (this.rootParams.defaultOrder && !(this.rootParams.orderBy && this.rootParams.orderBy.length)) {
        //     this.rootParams.orderBy = this.rootParams.defaultOrder;
        // }
        let data;
        if (this.rootParams.values) {
            data = [this.rootParams.values];
            delete this.rootParams.values;
        } else {
            data = await this.keepLast.add(this._loadData(this.rootParams));
        }
        this.root = this._createRoot(this.rootParams, data);
        window.root = this.root;
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    _createRoot(params, data) {
        const rootParams = {
            activeFields: params.activeFields,
            fields: params.fields,
            resModel: params.resModel,
            context: params.context,
            data,
        };
        if (params.viewMode === "form") {
            rootParams.data = rootParams.data[0];
            return new Record(this, {
                ...rootParams,
                mode: params.mode,
                resIds: params.resIds,
            });
        } else {
            const listParams = {
                ...rootParams,
                domain: params.domain,
                groupBy: params.groupBy,
                orderBy: params.orderBy,
                limit: params.limit,
                offset: params.offset || 0,
            };
            if (params.groupBy.length) {
                return new DynamicGroupList(this, listParams);
            } else {
                return new DynamicRecordList(this, listParams);
            }
        }
    }

    async _loadData(params) {
        console.log("coucou load");
        const fieldSpec = getFieldsSpec(params.activeFields, params.fields);
        console.log(fieldSpec);
        const unityReadSpec = {
            context: { ...params.context, bin_size: true },
            fields: fieldSpec,
        };
        if (params.viewMode === "form") {
            if (!params.resId) {
                // FIXME: this will be handled by unity at some point
                return this._loadNewRecord(params);
            }
            unityReadSpec.method = "read";
            unityReadSpec.ids = [params.resId];
        } else {
            if (params.groupBy.length) {
                // FIXME: this *might* be handled by unity at some point
                return this._loadGroupedList(params);
            }
            unityReadSpec.method = "search";
            unityReadSpec.domain = params.domain;
            unityReadSpec.offset = params.offset;
            unityReadSpec.limit = params.limit;
        }
        const response = await this.orm.call(params.resModel, "unity_read", [], unityReadSpec);
        console.log(response);
        return response[0];
    }

    async _loadGroupedList(params) {
        console.log("load group", params);
        const firstGroupByName = params.groupBy[0].split(":")[0];
        const _orderBy = params.orderBy.filter(
            (o) => o.name === firstGroupByName || params.fields[o.name].group_operator !== undefined
        );
        const orderby = orderByToString(_orderBy);
        const response = await this.orm.webReadGroup(
            params.resModel,
            params.domain,
            unique([...Object.keys(params.activeFields), firstGroupByName]),
            [params.groupBy[0]], // TODO: expand attribute in list views
            {
                orderby,
                lazy: true, // maybe useless
                offset: params.offset,
                limit: params.limit,
                context: params.context,
            }
        );
        const { groups, length } = response;
        for (const group of groups) {
            const groupBy = params.groupBy.slice(1);
            const response = await this._loadData({
                ...params,
                domain: params.domain.concat(group.__domain),
                groupBy,
            });
            if (groupBy.length) {
                group.groups = response.groups;
            } else {
                group.records = response.records;
            }
        }
        console.log(groups);
        window.groups = groups;
        return { groups, length };
    }

    async _loadNewRecord(params) {
        const onChangeSpec = {};
        const _populateOnChangeSpec = (activeFields, path = false) => {
            const prefix = path ? `${path}.` : "";
            for (const [fieldName, field] of Object.entries(activeFields)) {
                const key = `${prefix}${fieldName}`;
                onChangeSpec[key] = field.onChange ? "1" : "";
                if (field.related) {
                    _populateOnChangeSpec(field.related.activeFields, key);
                }
            }
            return onChangeSpec;
        };
        _populateOnChangeSpec(params.activeFields);
        window.onChangeSpec = onChangeSpec;
        const response = await this.orm.call(
            params.resModel,
            "onchange",
            [[], {}, [], onChangeSpec],
            { context: params.context }
        );
        window.response = response;
        const record = {};
        for (const [fieldName, value] of Object.entries(response.value)) {
            switch (params.fields[fieldName].type) {
                case "one2many":
                case "many2many": {
                    record[fieldName] = []; // TODO: process commands... how?
                    break;
                }
                default: {
                    record[fieldName] = value;
                }
            }
        }
        return [record];
    }

    async loadRecord({ resModel, resId, activeFields, fields, context }) {
        const fieldSpec = getFieldsSpec(activeFields, fields);
        const unityReadSpec = {
            context: { ...context, bin_size: true },
            fields: fieldSpec,
        };
        unityReadSpec.method = "read";
        unityReadSpec.ids = [resId];
        const [records] = await this.orm.call(resModel, "unity_read", [], unityReadSpec);
        return records[0];
    }

    async loadNewRecord(params) {
        const records = await this._loadNewRecord(params);
        return records[0];
    }
}

RelationalModel.services = ["user", "company", "notification"];
RelationalModel.Record = Record;
RelationalModel.Group = Group;
RelationalModel.DynamicRecordList = DynamicRecordList;
RelationalModel.DynamicGroupList = DynamicGroupList;
RelationalModel.StaticList = StaticList;
