/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { isRelational } from "@web/views/helpers/view_utils";
import {
    DynamicGroupList,
    DynamicRecordList,
    Group,
    RelationalModel,
} from "@web/views/relational_model";

/**
 * @typedef ProgressValue
 * @property {number} count
 * @property {any} value
 * @property {string} color
 * @property {string} string
 */

const { DateTime } = luxon;
const { EventBus } = owl;

const FALSE = Symbol("false");

const isValueEqual = (v1, v2) => (v1 instanceof DateTime ? v1.equals(v2) : v1 === v2);

const useTransaction = () => {
    const bus = new EventBus();
    let started = false;
    return {
        start: () => {
            if (started) {
                throw new Error(`Transaction in progress: commit or abort to start a new one.`);
            }
            started = true;
            bus.trigger("START");
        },
        commit: () => {
            if (!started) {
                throw new Error(`No transaction in progress.`);
            }
            started = false;
            bus.trigger("COMMIT");
        },
        abort: () => {
            if (!started) {
                throw new Error(`No transaction in progress.`);
            }
            started = false;
            bus.trigger("ABORT");
        },
        register: ({ onStart, onCommit, onAbort }) => {
            let currentData = null;
            bus.addEventListener("START", () => onStart && (currentData = onStart()));
            bus.addEventListener("COMMIT", () => onCommit && onCommit(currentData));
            bus.addEventListener("ABORT", () => onAbort && onAbort(currentData));
        },
    };
};

class KanbanGroup extends Group {
    constructor(model, params, state = {}) {
        super(...arguments);

        /** @type {ProgressValue[]} */
        this.progressValues = this._generateProgressValues();
        this.activeProgressValue = state.activeProgressValue || null;
        this.model.transaction.register({
            onStart: () => ({
                count: this.count,
                progressValues: [...this.progressValues],
                records: [...this.list.records],
            }),
            onAbort: ({ count, progressValues, records }) => {
                this.count = count;
                this.progressValues = progressValues;
                this.list.records = records;
            },
        });
    }

    get hasActiveProgressValue() {
        return this.model.progressAttributes && this.activeProgressValue !== null;
    }

    exportState() {
        return {
            ...super.exportState(),
            activeProgressValue: this.activeProgressValue,
        };
    }

    /**
     * @override
     */
    getAggregableRecords() {
        const records = super.getAggregableRecords();
        if (!this.hasActiveProgressValue) {
            return records;
        }
        const { fieldName } = this.model.progressAttributes;
        let recordsFilter;
        if (this.activeProgressValue === FALSE) {
            const values = this.progressValues
                .map((pv) => pv.value)
                .filter((val) => val !== this.activeProgressValue);
            recordsFilter = (r) => !values.includes(r.data[fieldName]);
        } else {
            recordsFilter = (r) => r.data[fieldName] === this.activeProgressValue;
        }
        return records.filter(recordsFilter);
    }

    /**
     * @override
     */
    quickCreate(fields, context) {
        const ctx = { ...context };
        if (this.hasActiveProgressValue && this.activeProgressValue !== FALSE) {
            const { fieldName } = this.model.progressAttributes;
            ctx[`default_${fieldName}`] = this.activeProgressValue;
        }
        return super.quickCreate(fields, ctx);
    }

    async filterProgressValue(value) {
        const { fieldName } = this.model.progressAttributes;
        const domains = [this.groupDomain];
        this.activeProgressValue = this.activeProgressValue === value ? null : value;
        if (this.hasActiveProgressValue) {
            if (value === FALSE) {
                const values = this.progressValues
                    .map((pv) => pv.value)
                    .filter((val) => val !== value);
                domains.push(["!", [fieldName, "in", values]]);
            } else {
                domains.push([[fieldName, "=", this.activeProgressValue]]);
            }
        }
        this.list.isDirty = this.hasActiveProgressValue;
        this.list.domain = Domain.and(domains).toList();

        await this.list.load();
        this.model.notify();
    }

    /**
     * @override
     */
    empty() {
        super.empty();

        this.activeProgressValue = null;
        for (const progressValue of this.progressValues) {
            progressValue.count = 0;
        }
    }

    /**
     * @override
     */
    addRecord() {
        const record = super.addRecord(...arguments);
        if (this.model.progressAttributes) {
            const pv = this._findProgressValueFromRecord(record);
            pv.count++;
        }
        return record;
    }

    /**
     * @override
     */
    removeRecord() {
        const record = super.removeRecord(...arguments);
        if (this.model.progressAttributes) {
            const pv = this._findProgressValueFromRecord(record);
            pv.count--;
        }
        return record;
    }

    /**
     * @protected
     * @param {Object} record
     * @returns {ProgressValue}
     */
    _findProgressValueFromRecord(record) {
        const { fieldName } = this.model.progressAttributes;
        const value = record.data[fieldName];
        return (
            this.progressValues.find((pv) => pv.value === value) ||
            this.progressValues.find((pv) => pv.value === FALSE)
        );
    }

    /**
     * @protected
     * @returns {ProgressValue[]}
     */
    _generateProgressValues() {
        if (!this.model.progressAttributes) {
            return [];
        }
        const { colors, fieldName } = this.model.progressAttributes;
        const { selection: fieldSelection } = this.fields[fieldName];
        /** @type {[string | typeof FALSE, string][]} */
        const colorEntries = Object.entries(colors);
        const selection = fieldSelection && Object.fromEntries(fieldSelection);

        if (!colorEntries.some((v) => v[1] === "muted")) {
            colorEntries.push([FALSE, "muted"]);
        }

        return colorEntries.map(([value, color]) => {
            let string;
            if (value === FALSE) {
                string = this.model.env._t("Other");
            } else if (selection) {
                string = selection[value];
            } else {
                string = String(value);
            }
            return { count: 0, value, string, color };
        });
    }
}

class KanbanDynamicGroupList extends DynamicGroupList {
    /**
     * @override
     */
    async load() {
        const oldGroups = this.groups.map((g, i) => [g, i]);
        const oldGroupBy = this.groupByField.name;
        await this._loadWithProgressData(super.load());
        for (const [group, index] of oldGroups) {
            if (oldGroupBy === group.groupByField.name) {
                const newGroup = this.groups.find((g) => isValueEqual(g.value, group.value));
                if (!newGroup) {
                    group.empty();
                    this.groups.splice(index, 0, group);
                }
            }
        }
    }

    async moveRecord(dataRecordId, dataGroupId, refId, targetGroupId) {
        const sourceGroup = this.groups.find((g) => g.id === dataGroupId);
        const targetGroup = this.groups.find((g) => g.id === targetGroupId);

        if (!sourceGroup || !targetGroup) {
            return; // Groups have been re-rendered, old ids are ignored
        }

        this.model.transaction.start();

        // Quick update: moves the record at the right position and notifies components
        const record = sourceGroup.list.records.find((r) => r.id === dataRecordId);
        const refIndex = targetGroup.list.records.findIndex((r) => r.id === refId);
        targetGroup.addRecord(sourceGroup.removeRecord(record), refIndex >= 0 ? refIndex + 1 : 0);

        // Move from one group to another
        try {
            if (dataGroupId !== targetGroupId) {
                const value = isRelational(this.groupByField)
                    ? [targetGroup.value]
                    : targetGroup.value;
                await record.update(this.groupByField.name, value);
                await record.save();
            }
            await targetGroup.list.resequence();
        } catch (err) {
            this.model.transaction.abort();
            this.model.notify();
            throw err;
        }
        this.model.transaction.commit();
    }

    // ------------------------------------------------------------------------
    // Protected
    // ------------------------------------------------------------------------

    async _loadWithProgressData(...loadPromises) {
        // No progress attributes : normal load
        if (!this.model.progressAttributes) {
            return Promise.all(loadPromises);
        }

        // Progress attributes : load with progress bar data
        const { colors, fieldName, help, sumField } = this.model.progressAttributes;
        const progressPromise = this.model.orm.call(this.resModel, "read_progress_bar", [], {
            domain: this.domain,
            group_by: this.groupBy[0],
            progress_bar: {
                colors,
                field: fieldName,
                help,
                sum_field: sumField && sumField.name,
            },
            context: this.context,
        });

        const [progressData] = await Promise.all([progressPromise, ...loadPromises]);

        for (const group of this.groups) {
            /** @type {Record<string, number>} */
            const groupData = progressData[group.displayName || group.value] || {};
            /** @type {Map<string | symbol, number>} */
            const counts = new Map(groupData ? Object.entries(groupData) : [[FALSE, group.count]]);
            const total = [...counts.values()].reduce((acc, c) => acc + c, 0);
            counts.set(FALSE, group.count - total);
            for (const pv of group.progressValues) {
                pv.count = counts.get(pv.value) || 0;
            }
        }
    }
}

class KanbanDynamicRecordList extends DynamicRecordList {
    async moveRecord(dataRecordId, dataGroupId, refId) {
        this.model.transaction.start();

        // Quick update: moves the record at the right position and notifies components
        const record = this.records.find((r) => r.id === dataRecordId);
        const refIndex = this.records.findIndex((r) => r.id === refId);
        this.addRecord(this.removeRecord(record), refIndex >= 0 ? refIndex + 1 : 0);

        // Call resequence
        try {
            await this.resequence();
        } catch (err) {
            this.model.transaction.abort();
            this.model.notify();
            throw err;
        }
        this.model.transaction.commit();
    }
}

KanbanDynamicRecordList.DEFAULT_LIMIT = 40;

export class KanbanModel extends RelationalModel {
    setup(params) {
        super.setup(...arguments);

        this.progressAttributes = params.progressAttributes;
        this.transaction = useTransaction();
    }

    /**
     * @override
     */
    hasData() {
        if (this.root.groups) {
            if (!this.root.groups.length) {
                // While we don't have any data, we want to display the column quick create and
                // example background. Return true so that we don't get sample data instead
                return true;
            }
            return this.root.groups.some((group) => group.list.records.length > 0);
        }
        return this.root.records.length > 0;
    }
}

KanbanModel.services = [...RelationalModel.services, "view"];
KanbanModel.DynamicGroupList = KanbanDynamicGroupList;
KanbanModel.DynamicRecordList = KanbanDynamicRecordList;
KanbanModel.Group = KanbanGroup;
