/* @odoo-module */

import { EventBus, markRaw } from "@odoo/owl";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { KeepLast, Mutex } from "@web/core/utils/concurrency";
import { unique } from "@web/core/utils/arrays";
import { session } from "@web/session";
import { Model } from "@web/views/model";
import { orderByToString } from "@web/views/utils";
import { Record } from "./record";
import { DynamicRecordList } from "./dynamic_record_list";
import { DynamicGroupList } from "./dynamic_group_list";
import { Group } from "./group";
import { StaticList } from "./static_list";
import { getFieldsSpec, getOnChangeSpec } from "./utils";

// WOWL TOREMOVE BEFORE MERGE
// Changes:
// checkValidity/askChanges/save/isDirty:
//  -> first two are now private and save checks if record isDirty -> can be
//     called even is not dirty (+ option "force" to bypass isDirty check)

export class RelationalModel extends Model {
    setup(params, { action, company, dialog, notification, rpc, user }) {
        this.action = action;
        this.company = company;
        this.dialog = dialog;
        this.notification = notification;
        this.rpc = rpc;
        this.user = user;
        const _invalidateCache = (resModel, method) => {
            if (!this.constructor.WRITE_METHODS.includes(method)) {
                return;
            }
            if (resModel === "res.currency") {
                return this.rpc("/web/session/get_session_info").then((result) => {
                    // FIXME: we should handle currencies in a service, to be able to reload them
                    // Also, reloading get_session_info only for currencies is a bit stupid
                    session.currencies = result.currencies;
                });
            }
            if (resModel === "res.company") {
                this.action.doAction("reload_context");
            }
            if (this.constructor.NOCACHE_MODELS.includes(resModel)) {
                this.env.bus.trigger("CLEAR-CACHES");
            }
        };
        const ormCall = this.orm.call.bind(this.orm);
        this.orm.call = async (model, method, args, kwargs) => {
            const result = await ormCall(model, method, args, kwargs);
            _invalidateCache(model, method);
            return result;
        };

        this.bus = new EventBus();

        this.keepLast = markRaw(new KeepLast());
        this.mutex = markRaw(new Mutex());

        this.rootParams = markRaw(params);

        this.countLimit = params.countLimit || this.constructor.WEB_SEARCH_READ_COUNT_LIMIT;

        this._urgentSave = false;
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
            data = this.rootParams.values;
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
            return new this.constructor.Record(this, {
                ...rootParams,
                mode: params.mode,
                resIds: params.resIds,
                onWillSaveRecord: params.onWillSaveRecord,
                onRecordSaved: params.onRecordSaved,
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
                return new this.constructor.DynamicGroupList(this, listParams);
            } else {
                return new this.constructor.DynamicRecordList(this, listParams);
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
        if (params.viewMode === "form") {
            const context = {
                ...params.context,
                active_id: params.resId,
                active_ids: [params.resId],
                active_model: params.resModel,
                current_company_id: this.company.currentCompany.id,
            };
            const records = await this._loadRecords({
                resModel: params.resModel,
                activeFields: params.activeFields,
                fields: params.fields,
                context,
                resIds: [params.resId],
            });
            return records[0];
        } else {
            return this._loadUngroupedList(params);
        }
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
        return await this._onchange({
            resModel: params.resModel,
            spec: getOnChangeSpec(params.activeFields),
            context: params.context,
        });
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

    async _loadRecords({ resModel, resIds, activeFields, fields, context }) {
        const kwargs = {
            context: { bin_size: true, ...context },
            fields: getFieldsSpec(activeFields, fields, context),
        };
        console.log("Unity field spec", kwargs.fields);
        const records = await this.orm.call(resModel, "web_read_unity", [resIds], kwargs);
        console.log("Unity response", records);
        return records;
    }

    async _loadUngroupedList({
        activeFields,
        context,
        domain,
        fields,
        limit,
        offset = 0,
        resModel,
    }) {
        const countLimit = Math.max(this.countLimit, offset + limit);
        const kwargs = {
            fields: getFieldsSpec(activeFields, fields, context),
            domain: domain,
            offset: offset,
            limit: limit,
            context: { bin_size: true, ...context },
        };
        if (countLimit !== Number.MAX_SAFE_INTEGER) {
            kwargs.count_limit = countLimit + 1;
        }
        console.log("Unity field spec", kwargs.fields);
        const response = await this.orm.call(resModel, "web_search_read_unity", [], kwargs);
        this.countLimit = countLimit;
        console.log("Unity response", response);
        return response;
    }
}

RelationalModel.services = ["action", "company", "dialog", "notification", "rpc", "user"];
RelationalModel.WRITE_METHODS = ["create", "write", "unlink", "action_archive", "action_unarchive"];
RelationalModel.NOCACHE_MODELS = [
    "ir.actions.act_window",
    "ir.filters",
    "ir.ui.view",
    "res.currency",
];
RelationalModel.Record = Record;
RelationalModel.Group = Group;
RelationalModel.DynamicRecordList = DynamicRecordList;
RelationalModel.DynamicGroupList = DynamicGroupList;
RelationalModel.StaticList = StaticList;
RelationalModel.WEB_SEARCH_READ_COUNT_LIMIT = 10000;
