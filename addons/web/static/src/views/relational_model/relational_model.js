/* @odoo-module */

import { EventBus, markRaw } from "@odoo/owl";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { KeepLast, Mutex } from "@web/core/utils/concurrency";
import { unique } from "@web/core/utils/arrays";
import { Model } from "@web/views/model";
import { orderByToString } from "@web/views/utils";
import { Record } from "./record";
import { DynamicRecordList } from "./dynamic_record_list";
import { DynamicGroupList } from "./dynamic_group_list";
import { Group } from "./group";
import { StaticList } from "./static_list";
import { getFieldsSpec, getOnChangeSpec } from "./utils";

export class RelationalModel extends Model {
    // FIXME: ask sad :D without this, can't make instance of model reactive.
    // EventTarget might be added to the list of supported types in SUPPORTED_RAW_TYPES (owl)
    get [Symbol.toStringTag]() {
        return "Object";
    }

    setup(params, { company, dialog, notification, user }) {
        this.company = company;
        this.dialog = dialog;
        this.notification = notification;
        this.user = user;

        this.bus = new EventBus();

        this.keepLast = markRaw(new KeepLast());
        this.mutex = markRaw(new Mutex());

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
        if (params.viewMode === "form" && !params.resId) {
            // FIXME: this will be handled by unity at some point
            return this._loadNewRecord(params);
        }
        if (params.viewMode !== "form" && params.groupBy.length) {
            // FIXME: this *might* be handled by unity at some point
            return this._loadGroupedList(params);
        }
        const fieldSpec = getFieldsSpec(params.activeFields, params.fields);
        console.log("Unity field spec", fieldSpec);
        const unityReadSpec = {
            context: { ...params.context, bin_size: true },
            fields: fieldSpec,
        };
        if (params.viewMode === "form") {
            unityReadSpec.method = "read";
            unityReadSpec.ids = [params.resId];
        } else {
            unityReadSpec.method = "search";
            unityReadSpec.domain = params.domain;
            unityReadSpec.offset = params.offset;
            unityReadSpec.limit = params.limit;
        }
        const response = await this.orm.call(params.resModel, "unity_read", [], unityReadSpec);
        console.log("Unity response", response);
        return response[0];
    }

    async _loadGroupedList(params) {
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
        return { groups, length };
    }

    async _loadNewRecord(params) {
        const values = await this._onchange({
            resModel: params.resModel,
            spec: getOnChangeSpec(params.activeFields),
            context: params.context,
        });
        const record = {};
        for (const [fieldName, value] of Object.entries(values)) {
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

    async _onchange({ resModel, spec, resIds, changes, fieldNames, context }) {
        console.log("Onchange spec", spec);
        const args = [resIds || [], changes || {}, fieldNames || [], spec];
        const response = await this.orm.call(resModel, "onchange2", args, { context });
        console.log("Onchange response", response);
        if (response.warning) {
            const { type, title, message, className, sticky } = response.warning;
            if (type === "dialog") {
                this.dialog.add(WarningDialog, { title, message });
            } else {
                this.notification.add(message, {
                    className,
                    sticky,
                    title,
                    type: "warning",
                });
            }
        }
        return response.value;
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

RelationalModel.services = ["company", "dialog", "notification", "user"];
RelationalModel.Record = Record;
RelationalModel.Group = Group;
RelationalModel.DynamicRecordList = DynamicRecordList;
RelationalModel.DynamicGroupList = DynamicGroupList;
RelationalModel.StaticList = StaticList;
