import { RelationalModel } from "@web/model/relational_model/relational_model";
import { DynamicRecordList } from "@web/model/relational_model/dynamic_record_list";
import { getFieldsSpec, getId } from "@web/model/relational_model/utils";
import { orderByToString } from "@web/search/utils/order_by";

export class HierarchyDynamicRecordList extends DynamicRecordList {
    _setData(data) {
        super._setData(data);
        this.parent = data.parent ? this._createRecordDatapoint(data.parent) : false;
    }
}

export class HierarchyModel extends RelationalModel {
    static DynamicRecordList = HierarchyDynamicRecordList;

    setup(params, services) {
        super.setup(params, services);
        this.parentFieldName = params.parentFieldName;
        this.childFieldName = params.childFieldName;
    }

    async _loadData(config, cache) {
        if (config.isMonoRecord || config.resIds) {
            return super._loadData(config, cache);
        }

        Object.assign(config, {
            loadId: getId("load"),
            limit: config.limit || this.initialLimit,
            countLimit: "countLimit" in config ? config.countLimit : this.initialCountLimit,
            offset: config.offset || 0,
        });

        const orm = cache ? this.orm.cache(cache) : this.orm;
        return orm.call(config.resModel, "hierarchy_read", [], {
            domain: config.domain,
            specification: getFieldsSpec(config.activeFields, config.fields, config.context),
            parent_field_name: this.parentFieldName,
            roots_only: this.env.searchModel?.facets.length === 0 && !config.context.hierarchy_parent_id,
            offset: config.offset,
            limit: config.limit,
            order: orderByToString(config.orderBy.filter((o) => o.name !== "__count")),
            count_limit: config.countLimit !== Number.MAX_SAFE_INTEGER ? config.countLimit + 1 : undefined,
            context: config.context,
        });
    }

    _createRoot(config, data) {
        return new this.constructor.DynamicRecordList(this, config, data);
    }
}
