import { Domain } from "@web/core/domain";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { DynamicGroupList } from "@web/model/relational_model/dynamic_group_list";
import { Record as RelationalRecord } from "@web/model/relational_model/record";

export class HierarchyRecord extends RelationalRecord {
    get areChildrenLoaded() {
        const group = this.childGroup;
        return !!(group && !group.isFolded);
    }

    get childCount() {
        return this.data[this.model.childFieldName]?.count || 0;
    }

    get childGroup() {
        return this.model.root?.isGrouped
            ? this.model.root.groups?.find((group) => group.value === this.resId)
            : null;
    }

    get parentResId() {
        return this.data[this.model.parentFieldName]?.id || false;
    }

    toggleChildren() {
        const targetParentResId = this.areChildrenLoaded
            ? this.parentResId
            : this.resId;
        this.model.load({ targetParentResId });
    }
}

export class HierarchyDynamicGroupList extends DynamicGroupList {
    _setData(data) {
        const parentIdPerResId = new Map(data.groups.flatMap((group) => group.records.map((record) => [record.id, group.value])));
        const depthPerParentId = new Map([[false, 0]]);

        const getDepth = (parentId, visited = new Set()) => {
            if (depthPerParentId.has(parentId)) {
                return depthPerParentId.get(parentId);
            }
            // parent not loaded (orphan) or cycle: place the group right after the roots
            if (!parentIdPerResId.has(parentId) || visited.has(parentId)) {
                return 1;
            }
            visited.add(parentId);
            const depth = 1 + getDepth(parentIdPerResId.get(parentId), visited);
            depthPerParentId.set(parentId, depth);
            return depth;
        };

        super._setData({
            ...data,
            groups: [...data.groups].sort((g1, g2) => getDepth(g1.value) - getDepth(g2.value)),
        });
    }
}

export class HierarchyModel extends RelationalModel {
    static Record = HierarchyRecord;
    static DynamicGroupList = HierarchyDynamicGroupList;

    setup(params, services) {
        super.setup(params, services);
        this.parentFieldName = params.parentFieldName;
        this.childFieldName = params.childFieldName;
    }

    /**
     * Evaluate if the current search query is the default one.
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

    /**
     * Get the next model config to use
     *
     * @param {Object} currentConfig current model config used
     * @param {Object} params new params
     * @returns {Object} new model config to use
     */
    _getNextConfig(currentConfig, params) {
        const searchDomain = params.domain || currentConfig.searchDomain || [];

        let targetParentResId;
        if ('targetParentResId' in params) {
            targetParentResId = params.targetParentResId || false;
        } else if ('domain' in params && this.isReady()) {
            targetParentResId = false;
        } else if (
            !this.isReady() &&
            !("targetParentResId" in currentConfig) &&
            params.context?.target_parent_res_id &&
            this.isSearchDefaultOrEmpty()
        ) {
            targetParentResId = params.context.target_parent_res_id;
        } else {
            targetParentResId = currentConfig.targetParentResId || false;
        }

        let coDomain;
        let groupBy = [];
        if (targetParentResId) {
            coDomain = Domain.or([
                [[this.parentFieldName, 'parent_of', targetParentResId]],
                [[this.parentFieldName, '=', targetParentResId]],
            ]);
            groupBy = [this.parentFieldName];
        } else if (this.isSearchDefaultOrEmpty()) {
            coDomain = [[this.parentFieldName, '=', false]];
        }

        const config = super._getNextConfig(currentConfig, {
            ...params,
            domain: coDomain ? Domain.and([searchDomain, coDomain]).toList() : searchDomain,
            groupBy,
        });

        let limit;
        if (groupBy.length) {
            limit = Number.MAX_SAFE_INTEGER;
        } else {
            limit = currentConfig.groupBy?.length ? this.initialLimit : config.limit || this.initialLimit;
        }

        return {
            ...config,
            searchDomain,
            targetParentResId,
            openGroupsByDefault: true,
            openDefaultGroupByDefault: true,
            limit,
            context: { ...config.context, max_number_opened_groups: Number.MAX_SAFE_INTEGER },
        };
    }
}
