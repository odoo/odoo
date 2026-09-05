//@ts-check

import { Domain } from "@web/core/domain";
import { DynamicList } from "./dynamic_list";
import { getGroupServerValue } from "./utils";

export const MOVABLE_RECORD_TYPES = ["char", "boolean", "integer", "selection", "many2one"];

/**
 * @typedef {import("./group").Group} Group
 * @typedef {import("./record").Record} RelationalRecord
 */

export class DynamicGroupList extends DynamicList {
    static type = "DynamicGroupList";

    /** @readonly */
    isGrouped = true;

    /**
     * @type {DynamicList["setup"]}
     */
    setup(_config, data) {
        super.setup(...arguments);

        this.groups = [];
        this._nbRecordsMatchingDomain = null;
        this._setData(data);
    }

    /**
     * @param {Record<string, unknown>} data
     */
    _setData(data) {
        /** @type {Group[]} */
        this.groups = data.groups.map((g) => this._createGroupDatapoint(g));
        this.count = data.length;
        this._selectDomain(this.isDomainSelected);
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get groupBy() {
        return this.config.groupBy;
    }

    get groupByField() {
        return this.fields[this.groupBy[0].split(":")[0]];
    }

    get hasData() {
        return this.groups.some((group) => group.hasData);
    }

    get isRecordCountTrustable() {
        return this.count <= this.limit || this._nbRecordsMatchingDomain !== null;
    }

    /**
     * List of loaded records inside groups.
     * @returns {RelationalRecord[]}
     */
    get records() {
        return this.groups.filter((group) => !group.isFolded).flatMap((group) => group.records);
    }

    /**
     * @returns {number}
     */
    get recordCount() {
        if (this._nbRecordsMatchingDomain !== null) {
            return this._nbRecordsMatchingDomain;
        }
        return this.groups.reduce((acc, group) => acc + group.count, 0);
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * @param {string} groupName
     * @param {string} [foldField] if given, will write true on this field to
     *   make the group folded by default
     */
    async createGroup(groupName, foldField) {
        if (!this.groupByField || this.groupByField.type !== "many2one") {
            throw new Error("Cannot create a group on a non many2one group field");
        }

        await this.model.mutex.exec(() => this._createGroup(groupName, foldField));
    }

    async deleteGroups(groups) {
        await this.model.mutex.exec(() => this._deleteGroups(groups));
    }

    /**
     * Among the records moved together by `moveRecord`, the ones that will actually
     * change group, i.e. the ones not already in the target group. Meant for overrides
     * reacting to the new group value, and thus empty when the move can't happen.
     *
     * @param {string[]} recordIds
     * @param {string} targetGroupId
     * @returns {RelationalRecord[]} in display order
     */
    getChangingGroupRecords(recordIds, targetGroupId) {
        if (!this.groups.some((group) => group.id === targetGroupId)) {
            return [];
        }
        return this.groups
            .filter((group) => group.id !== targetGroupId)
            .flatMap((group) => group.list.records.filter((r) => recordIds.includes(r.id)));
    }

    /**
     * @param {string[]} recordIds ids of the records moved together, in display order,
     *  possibly from several groups
     * @param {string} refId
     * @param {string} targetGroupId
     */
    async moveRecord(recordIds, refId, targetGroupId) {
        const targetGroup = this.groups.find((g) => g.id === targetGroupId);
        if (!targetGroup) {
            return;
        }
        // the records to move, with the group and index they come from, in display order
        const moved = this.groups.flatMap((group) =>
            group.list.records
                .map((record, index) => ({ record, group, index }))
                .filter(({ record }) => recordIds.includes(record.id))
        );
        const recordsToUpdate = this.getChangingGroupRecords(recordIds, targetGroupId);

        const resequenceTargetGroup = () =>
            targetGroup.list._resequence(targetGroup.list.records, this.resModel, recordIds, refId);

        if (moved.every(({ group }) => group === targetGroup)) {
            return resequenceTargetGroup();
        }

        // step 1: move the records to their new position
        const sourceGroups = new Set(moved.map(({ group }) => group));
        // if a source group contains more records than what's loaded, reload it afterwards
        const groupsToReload = [...sourceGroups].filter(
            (group) =>
                group !== targetGroup && group.list.count > group.list.offset + group.list.limit
        );
        for (const group of sourceGroups) {
            group._removeRecords(recordIds);
        }
        // computed after the removals, as the target group may itself be a source group
        const refIndex = targetGroup.list.records.findIndex((r) => r.id === refId);
        moved.forEach(({ record }, i) => targetGroup._addRecord(record, refIndex + 1 + i));
        const revert = () => {
            targetGroup._removeRecords(recordIds);
            for (const { record, group, index } of moved) {
                group._addRecord(record, index);
            }
        };

        // step 2: write the target group value on the records that changed group
        let value = targetGroup.value;
        if (targetGroup.groupByField.type === "many2one") {
            value = value ? { id: value, display_name: targetGroup.displayName } : false;
        }
        const changes = { [targetGroup.groupByField.name]: value };
        try {
            if (!(await this._saveRecords(recordsToUpdate, changes))) {
                return revert();
            }
        } catch (e) {
            revert();
            throw e;
        }

        // step 3: reload the truncated source groups and resequence the target group
        const proms = groupsToReload.map((group) => {
            const { offset, limit, orderBy, domain } = group.list;
            return group.list._load(offset, limit, orderBy, domain);
        });
        if (!targetGroup.isFolded) {
            proms.push(resequenceTargetGroup());
        }
        return Promise.all(proms);
    }

    /**
     * Moves a group after another one. Groups are dragged one at a time, unlike the
     * records they hold, which are moved with `moveRecord`.
     *
     * @param {string} movedGroupId
     * @param {string} targetGroupId
     */
    async resequence(movedGroupId, targetGroupId) {
        if (!this.groupByField || this.groupByField.type !== "many2one") {
            throw new Error("Cannot resequence a group on a non many2one group field");
        }

        return this.model.mutex.exec(async () => {
            await this._resequence(
                this.groups,
                this.groupByField.relation,
                [movedGroupId],
                targetGroupId
            );
        });
    }

    async selectDomain(value) {
        return this.model.mutex.exec(async () => {
            await this._ensureCorrectRecordCount();
            this._selectDomain(value);
        });
    }

    async sortBy(fieldName) {
        if (!this.groups.length) {
            return;
        }
        if (this.groups.every((group) => group.isFolded)) {
            // all groups are folded
            if (this.groupByField.name !== fieldName) {
                // grouped by another field than fieldName
                if (!(fieldName in this.groups[0].aggregates)) {
                    // fieldName has no aggregate values
                    return;
                }
            }
        }
        return super.sortBy(fieldName);
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    async _createGroup(groupName, foldField = false) {
        const [id] = await this.model.orm.call(
            this.groupByField.relation,
            "name_create",
            [groupName],
            { context: this.context }
        );
        if (foldField) {
            await this.model.orm.write(
                this.groupByField.relation,
                [id],
                { [foldField]: true },
                { context: this.context }
            );
        }
        const lastGroup = this.groups.at(-1);

        // This is almost a copy/past of the code in relational_model.js
        // Maybe we can create an addGroup method in relational_model.js
        // and call it from here and from relational_model.js
        const commonConfig = {
            resModel: this.config.resModel,
            fields: this.config.fields,
            activeFields: this.config.activeFields,
            fieldsToAggregate: this.config.fieldsToAggregate,
        };
        const context = {
            ...this.context,
            [`default_${this.groupByField.name}`]: id,
        };
        const nextConfigGroups = { ...this.config.groups };
        const domain = Domain.and([this.domain, [[this.groupByField.name, "=", id]]]).toList();
        const groupBy = this.groupBy.slice(1);
        nextConfigGroups[id] = {
            ...commonConfig,
            context,
            groupByFieldName: this.groupByField.name,
            isFolded: Boolean(foldField),
            value: id,
            extraDomain: false,
            initialDomain: domain,
            list: {
                ...commonConfig,
                context,
                domain: domain,
                groupBy,
                orderBy: this.orderBy,
                limit: this.model.initialLimit,
                offset: 0,
            },
        };
        this.model._updateConfig(this.config, { groups: nextConfigGroups }, { reload: false });

        const data = {
            aggregates: {},
            count: 0,
            length: 0,
            __domain: domain,
            [this.groupByField.name]: [id, groupName],
            value: id,
            serverValue: getGroupServerValue(this.groupByField, id),
            displayName: groupName,
            rawValue: [id, groupName],
        };
        if (groupBy.length) {
            data.groups = [];
        } else {
            data.records = [];
        }

        const group = this._createGroupDatapoint(data);
        if (lastGroup) {
            const groups = [...this.groups, group];
            await this._resequence(groups, this.groupByField.relation, [group.id], lastGroup.id);
            this.groups = groups;
        } else {
            this.groups.push(group);
        }
    }

    _createGroupDatapoint(data) {
        const config = this.config.groups[data.value];
        return new this.model.constructor.Group(this.model, config, data, { parent: this });
    }

    async _deleteGroups(groups) {
        const shouldReload = groups.some((g) => g.count > 0);
        const succeeded = await this._unlinkGroups(groups);
        if (succeeded === false) {
            return;
        }
        const configGroups = { ...this.config.groups };
        for (const group of groups) {
            delete configGroups[group.value];
        }
        if (shouldReload) {
            await this.model._updateConfig(
                this.config,
                { groups: configGroups },
                { commit: this._setData.bind(this) }
            );
        } else {
            for (const group of groups) {
                this._removeGroup(group);
            }
            this.model._updateConfig(this.config, { groups: configGroups }, { reload: false });
        }
    }

    async _ensureCorrectRecordCount() {
        if (!this.isRecordCountTrustable) {
            this._nbRecordsMatchingDomain = await this.model.orm.searchCount(
                this.resModel,
                this.domain,
                { limit: this.model.initialCountLimit }
            );
        }
    }

    _getDPresId(group) {
        return group.value;
    }

    _getDPFieldValue(group, handleField) {
        return group[handleField];
    }

    async _load(offset, limit, orderBy, domain) {
        await this.model._updateConfig(
            this.config,
            { offset, limit, orderBy, domain },
            { commit: this._setData.bind(this) }
        );
        if (this.isDomainSelected) {
            await this._ensureCorrectRecordCount();
        }
    }

    _removeGroup(group) {
        const index = this.groups.findIndex((g) => g.id === group.id);
        this.groups.splice(index, 1);
        this.count--;
    }

    _removeRecords(recordIds) {
        const proms = [];
        for (const group of this.groups) {
            proms.push(group._removeRecords(recordIds));
        }
        return Promise.all(proms);
    }

    _selectDomain(value) {
        for (const group of this.groups) {
            group.list._selectDomain(value);
        }
        super._selectDomain(value);
    }

    /**
     * Opens or folds all groups.
     *
     * @param {boolean} [fold=false] true to fold all groups, false to open them
     * @returns {Promise}
     */
    _toggleAllGroups(fold = false) {
        if (fold) {
            this.groups.forEach((group) => {
                if (!group.isFolded) {
                    group.toggle();
                }
            });
        } else {
            const nextGroupConfig = Object.fromEntries(
                Object.entries(this.config.groups).map(([groupId, groupConfig]) => [
                    groupId,
                    Object.assign({}, groupConfig, { isFolded: fold }),
                ])
            );
            return this.model._updateConfig(
                this.config,
                { groups: nextGroupConfig },
                { commit: this._setData.bind(this) }
            );
        }
    }

    async _toggleSelection() {
        if (!this.records.length) {
            // all groups are folded, so there's no visible records => select all domain
            if (!this.isDomainSelected) {
                await this._ensureCorrectRecordCount();
                this._selectDomain(true);
            } else {
                this._selectDomain(false);
            }
        } else {
            super._toggleSelection();
        }
    }

    _unlinkGroups(groups) {
        const groupResIds = groups.map((g) => g.value);
        return this.model.orm.unlink(this.groupByField.relation, groupResIds, {
            context: this.context,
        });
    }
}
