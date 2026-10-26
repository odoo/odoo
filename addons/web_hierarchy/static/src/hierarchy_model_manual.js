import { Domain } from "@web/core/domain";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { DynamicGroupList } from "@web/model/relational_model/dynamic_group_list";

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
    static DynamicGroupList = HierarchyDynamicGroupList;
    static forceAutoUnfold = true;

    setup(params, services) {
        super.setup(params, services);
        this.parentFieldName = params.parentFieldName;
        this.childFieldName = params.childFieldName;
    }

    /**
     * Set a new parent to the given record, after checking it does not create a cycle.
     * 
     * @param {Record} record 
     * @param {number | false} parentResId 
     * @returns {Promise<boolean>} true if the parent has been updated.
     */
    async updateParent(record, parentResId) {
        if (parentResId === record.data[this.parentFieldName]?.id) {
            return false;
        }
        if (parentResId === record.resId) {
            this.notification.add(_t('The parent record cannot be the record itself.'), { type: 'danger' });
            return false;
        }
        if (parentResId) {
            const isDescendant = await this.orm.searchCount(this.config.resModel, [
                ['id', '=', parentResId],
                [this.parentFieldName, 'child_of', record.resId],
            ]);
            if (isDescendant) {
                this.notification.add(_t('Cannot change the parent because it will cause a cyclic.'), { type: 'danger' });
                return false;
            }
        }
        return this.mutex.exec(() => this._updateParentId(record.resId, parentResId));
    }

    /**
     * ORM call to update the parent of a record.
     */
    async _updateParentId(recordResId, parentResId) {
        return this.orm.write(
            this.config.resModel,
            [recordResId],
            { [this.parentFieldName]: parentResId },
            { context: this.config.context }
        );
    }

    /**
     * Get the next model config to use
     *
     * @param {Object} currentConfig current model config used
     * @param {Object} params new params
     * @returns {Object} new model config to use
     */
    _getNextConfig(currentConfig, params) {
        let isNewSearch = false;
        let domain = [[this.parentFieldName, '=', false]];
        let { searchDomain = [], targetParentResId = false } = currentConfig;

        if ('domain' in params) {
            isNewSearch = new Domain(params.domain).toString() !== new Domain(searchDomain).toString();
            searchDomain = params.domain;
        }

        if ('targetParentResId' in params) {
            targetParentResId = params.targetParentResId;
        } else if (isNewSearch) {
            targetParentResId = false;
        }

        if (targetParentResId) {
            domain = Domain.or([
                [[this.parentFieldName, 'parent_of', targetParentResId]],
                [[this.parentFieldName, '=', targetParentResId]],
            ]).toList();
        } else if (searchDomain.length > 0) {
            domain = Domain.and([
                searchDomain,
                [[this.childFieldName, "any", searchDomain]],
            ]).toList();
        }

        return {
            ...super._getNextConfig(currentConfig, {
                ...params,
                domain,
                groupBy: [this.parentFieldName],
            }),
            searchDomain,
            targetParentResId,
            openGroupsByDefault: true,
        };
    }
}
