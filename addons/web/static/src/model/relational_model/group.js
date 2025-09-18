// @ts-check

/** @module @web/model/relational_model/group - Single group node within a grouped list, holding aggregates and a nested record list */

import { Domain } from "@web/core/domain";

import { DataPoint } from "./datapoint";
/** @import { RelationalModelConfig } from "./relational_model" */

export class Group extends DataPoint {
    static type = "Group";

    /**
     * @param {RelationalModelConfig & { groupByFieldName: string, list: any, record?: any }} config
     * @param {Record<string, any>} data
     */
    setup(config, data) {
        super.setup(config, data);
        this.groupByField = this.fields[config.groupByFieldName];
        this.range = data.range;
        this._rawValue = data.rawValue;
        /** @type {number} */
        this.count = data.count;
        this.value = data.value;
        this.serverValue = data.serverValue;
        this.displayName = data.displayName;
        this.aggregates = data.aggregates;
        let List;
        if (config.list.groupBy.length) {
            List = this.model.Class.DynamicGroupList;
        } else {
            List = this.model.Class.DynamicRecordList;
        }
        /** @type {any} DynamicRecordList or DynamicGroupList depending on groupBy depth */
        this.list = new List(this.model, config.list, data);
        this._useGroupCountForList();
        if (config.record) {
            config.record.context = {
                ...config.record.context,
                ...config.context,
            };
            this.record = new this.model.Class.Record(
                this.model,
                config.record,
                data.values,
            );
        }
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get groupDomain() {
        return this.config.initialDomain;
    }
    get hasData() {
        return this.count > 0;
    }
    get isFolded() {
        return this.config.isFolded;
    }
    get records() {
        return this.list.records;
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    async addExistingRecord(resId, atFirstPosition = false) {
        const record = await this.list.addExistingRecord(resId, atFirstPosition);
        this.count++;
        return record;
    }

    async addNewRecord(_unused, atFirstPosition = false) {
        const canProceed = await this.model.root.leaveEditMode();
        if (canProceed) {
            const record = await this.list.addNewRecord(atFirstPosition);
            if (record) {
                this.count++;
            }
        }
    }

    async applyFilter(filter) {
        if (filter) {
            await this.list.load({
                domain: Domain.and([this.groupDomain, filter]).toList(),
            });
        } else {
            await this.list.load({ domain: this.groupDomain });
            this.count = this.list.isGrouped ? this.list.recordCount : this.list.count;
        }
        this.model._updateConfig(
            this.config,
            { extraDomain: filter },
            { reload: false },
        );
    }

    deleteRecords(records) {
        return this.model.mutex.exec(() => this._deleteRecords(records));
    }

    async toggle() {
        if (this.config.isFolded) {
            await this.list.load();
        }
        this._useGroupCountForList();
        this.model._updateConfig(
            this.config,
            { isFolded: !this.config.isFolded },
            { reload: false },
        );
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    _addRecord(record, index) {
        this.list._addRecord(record, index);
        this.count++;
    }

    async _deleteRecords(records) {
        await this.list._deleteRecords(records);
        this.count -= records.length;
    }

    /**
     * The count returned by web_search_read is limited (see DEFAULT_COUNT_LIMIT). However, the one
     * returned by formatted_read_group, for each group, isn't. So in the grouped case, it might happen
     * that the group count is more accurate than the list one. It that case, we use it on the list.
     */
    _useGroupCountForList() {
        if (!this.list.isGrouped && this.list.count === this.list.config.countLimit) {
            this.list.count = this.count;
        }
    }

    async _removeRecords(recordIds) {
        const idsToRemove = recordIds.filter((id) =>
            this.list.records.some((r) => r.id === id),
        );
        this.list._removeRecords(idsToRemove);
        this.count -= idsToRemove.length;
    }
}
