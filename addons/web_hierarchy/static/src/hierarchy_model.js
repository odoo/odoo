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

    /**
     * Whether the current search is the default one of the view, or empty.
     * In that case, only the roots of the hierarchy are loaded. The search
     * items of the disabled menu types (e.g. group by) are ignored.
     *
     * @returns {boolean}
     */
    isSearchDefaultOrEmpty() {
        if (!this.env.searchModel) {
            return true;
        }
        const isDisabledOptionalSearchMenuType = (type) => {
            return (
                ["filter", "groupBy", "favorite"].includes(type) &&
                !this.env.searchModel.searchMenuTypes.has(type)
            );
        };
        const activeSearchItems = this.env.searchModel.getSearchItems(
            (item) => item.isActive && !isDisabledOptionalSearchMenuType(item.type)
        );
        if (!activeSearchItems.length) {
            return true;
        }
        const defaultSearchItems = this.env.searchModel.getSearchItems(
            (item) =>
                item.isDefault &&
                item.type !== "favorite" &&
                !isDisabledOptionalSearchMenuType(item.type)
        );
        return JSON.stringify(defaultSearchItems) === JSON.stringify(activeSearchItems);
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
            roots_only: this.isSearchDefaultOrEmpty(),
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
