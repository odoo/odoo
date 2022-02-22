/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { isRelational } from "@web/views/helpers/view_utils";
import {
    DynamicGroupList,
    DynamicRecordList,
    Group,
    RelationalModel,
} from "@web/views/relational_model";

const { EventBus } = owl;

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

        this.activeProgressValue = state.activeProgressValue || null;
        this.progressValues = [];
        this.model.transaction.register({
            onStart: () => ({ count: this.count, records: [...this.list.records] }),
            onAbort: ({ count, records }) => {
                this.count = count;
                this.list.records = records;
            },
        });
    }

    get hasActiveProgressValue() {
        return this.activeProgressValue !== null;
    }

    exportState() {
        return {
            ...super.exportState(),
            activeProgressValue: this.activeProgressValue,
        };
    }

    async filterProgressValue(value) {
        const { fieldName } = this.model.progressAttributes;
        const domains = [this.groupDomain];
        this.activeProgressValue = this.activeProgressValue === value ? null : value;
        if (this.hasActiveProgressValue) {
            domains.push([[fieldName, "=", this.activeProgressValue]]);
        }
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
        this.progressValues = [];
    }

    /**
     * @override
     */
    async validateQuickCreate() {
        const record = await super.validateQuickCreate(...arguments);
        if (this.model.progressAttributes) {
            const { fieldName } = this.model.progressAttributes;
            const recordValue = record.data[fieldName];
            const value = recordValue === undefined ? false : recordValue;
            const progressValue = this.progressValues.find((pv) => pv.value === value);
            progressValue.count++;
        }
        return record;
    }
}

class KanbanDynamicGroupList extends DynamicGroupList {
    /**
     * @override
     */
    async load() {
        await this._loadWithProgressData(super.load());
    }

    /**
     * @override
     */
    async createGroup() {
        const group = await super.createGroup(...arguments);
        group.progressValues.push({
            count: 0,
            value: false,
            string: this.model.env._t("Other"),
            color: "muted",
        });
        return group;
    }

    async moveRecord(dataRecordId, dataGroupId, refId, newGroupId) {
        const oldGroup = this.groups.find((g) => g.id === dataGroupId);
        const newGroup = this.groups.find((g) => g.id === newGroupId);

        if (!oldGroup || !newGroup) {
            return; // Groups have been re-rendered, old ids are ignored
        }

        this.model.transaction.start();

        // Quick update: moves the record at the right position and notifies components
        const record = oldGroup.list.records.find((r) => r.id === dataRecordId);
        const refIndex = newGroup.list.records.findIndex((r) => r.id === refId);
        newGroup.addRecord(oldGroup.removeRecord(record), refIndex >= 0 ? refIndex + 1 : 0);

        // Move from one group to another
        try {
            if (dataGroupId !== newGroupId) {
                const value = isRelational(this.groupByField) ? [newGroup.value] : newGroup.value;
                await record.update(this.groupByField.name, value);
                await record.save();
                await this._loadWithProgressData(oldGroup.load(), newGroup.load());
            }
            await newGroup.list.resequence();
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

        const progressField = this.fields[fieldName];
        /** @type {[string | false, string][]} */
        const colorEntries = Object.entries(colors);
        const selection = Object.fromEntries(progressField.selection || []);

        if (!colorEntries.some((e) => e[1] === "muted")) {
            colorEntries.push([false, "muted"]);
        }

        for (const group of this.groups) {
            group.progressValues = [];
            const groupKey = group.displayName || group.value;
            const counts = progressData[groupKey] || { false: group.count };
            const remaining = group.count - Object.values(counts).reduce((acc, c) => acc + c, 0);
            for (const [key, color] of colorEntries) {
                const count = key === false ? remaining : counts[key];
                group.progressValues.push({
                    count: count || 0,
                    value: key,
                    string: selection[String(key)] || this.model.env._t("Other"),
                    color,
                });
            }
        }
    }
}

class KanbanDynamicRecordList extends DynamicRecordList {}

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
