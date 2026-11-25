import { DynamicRecordList } from "@web/model/relational_model/dynamic_record_list";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { getId, getFieldsSpec } from "@web/model/relational_model/utils";


class HierarchyList extends DynamicRecordList {
    _setData(data) {
        super._setData(data);
        this.children = new Map(data.children ?? []);
    }
}

export class HierarchyModel extends RelationalModel {
    static DynamicRecordList = HierarchyList;

    setup(params, services) {
        super.setup(params, services);
        this.parentFieldName = params.parentFieldName;
        this.childFieldName = params.childFieldName;
    }

    async _loadData(config, cache) {
        if (config.isMonoRecord || config.resIds) {
            return super._loadData(config, cache);
        }
        config.loadId = getId("load");
        config.limit ||= this.initialLimit;
        return this._loadUngroupedList(config, cache);
    }

    _getNextConfig(currentConfig, params) {
        const config = super._getNextConfig(currentConfig, {
            ...params,
            groupBy: [],
        });
        config.countLimit = Number.MAX_SAFE_INTEGER;
        config.offset = 0;
        return config;
    }

    async _loadUngroupedList(config, cache) {
        const orm = cache ? this.orm.cache(cache) : this.orm;
        const spec = getFieldsSpec(config.activeFields, config.fields, config.context);
        return orm.call(config.resModel, "hierarchy_read", [config.domain, spec, this.parentFieldName], {
            limit: config.limit,
            context: config.context,
        });
    }
}
