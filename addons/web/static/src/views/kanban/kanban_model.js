/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { isRelational } from "@web/views/utils";
import {
    DynamicGroupList,
    DynamicRecordList,
    Group,
    RelationalModel,
} from "@web/views/relational_model";
import { KeepLast } from "@web/core/utils/concurrency";

/**
 * @typedef ProgressBar
 * @property {number} count
 * @property {any} value
 * @property {string} color
 * @property {string} string
 */

import { EventBus, markRaw } from "@odoo/owl";

const FALSE = Symbol("false");

class TransactionInProgress extends Error {}

class NoTransactionInProgress extends Error {}

function makeTransactionManager() {
    const bus = new EventBus();
    const transactions = {};
    return {
        start: (id) => {
            if (transactions[id]) {
                throw new TransactionInProgress(
                    `Transaction in progress: commit or abort to start a new one.`
                );
            }
            transactions[id] = true;
            bus.trigger("START");
        },
        commit: (id) => {
            if (!transactions[id]) {
                throw new NoTransactionInProgress(`No transaction in progress.`);
            }
            delete transactions[id];
            bus.trigger("COMMIT");
        },
        abort: (id) => {
            if (!transactions[id]) {
                throw new NoTransactionInProgress(`No transaction in progress.`);
            }
            delete transactions[id];
            bus.trigger("ABORT");
        },
        register: ({ onStart, onCommit, onAbort }) => {
            let currentData = null;
            bus.addEventListener("START", () => onStart && (currentData = onStart()));
            bus.addEventListener("COMMIT", () => onCommit && onCommit(currentData));
            bus.addEventListener("ABORT", () => onAbort && onAbort(currentData));
        },
    };
}

class KanbanGroup extends Group {
    setup(_params, state = {}) {
        super.setup(...arguments);

        /** @type {ProgressBar[]} */
        this.progressBars = this._generateProgressBars();
        this.progressValue = markRaw(state.progressValue || { active: null });
        this.list.domain = this.getProgressBarDomain();
        this.tooltip = [];

        this.model.transaction.register({
            onStart: () => ({
                count: this.count,
                progressBars: [...this.progressBars],
                records: [...this.list.records],
            }),
            onAbort: ({ count, progressBars, records }) => {
                this.count = count;
                this.progressBars = progressBars;
                this.list.records = records;
            },
        });

        this.model.addEventListener("record-updated", ({ detail }) => {
            const { record, relatedRecords } = detail;
            const localIds = this.records.map((r) => r.id);
            const updatedIds = [record, ...relatedRecords].map((r) => r.id);
            if (localIds.some((id) => updatedIds.includes(id))) {
                this.model.trigger("group-updated", {
                    group: this,
                    withProgressBars: true,
                });
            }
        });
    }

    get activeProgressBar() {
        return (
            this.hasActiveProgressValue &&
            this.progressBars.find((pv) => pv.value === this.progressValue.active)
        );
    }

    get hasActiveProgressValue() {
        return this.model.hasProgressBars && this.progressValue.active !== null;
    }

    /**
     * @override
     */
    async deleteRecords() {
        const records = await super.deleteRecords(...arguments);
        this.model.trigger("group-updated", {
            group: this,
            withProgressBars: true,
        });
        return records;
    }

    /**
     * @override
     */
    empty() {
        super.empty();

        this.progressValue.active = null;
        for (const progressBar of this.progressBars) {
            progressBar.count = 0;
        }
    }

    /**
     * @override
     */
    exportState() {
        return {
            ...super.exportState(),
            progressValue: this.progressValue,
        };
    }

    /**
     * @override
     */
    quickCreate(activeFields, context) {
        const ctx = { ...context };
        if (this.hasActiveProgressValue && this.progressValue.active !== FALSE) {
            const { fieldName } = this.model.progressAttributes;
            ctx[`default_${fieldName}`] = this.progressValue.active;
        }
        return super.quickCreate(activeFields, ctx);
    }

    async load() {
        this.loadTooltip();
        await super.load();
    }

    /**
     * Requests the groups tooltips to the server and store them in this.tooltip
     *
     * @returns {Promise<void>}
     */
    async loadTooltip() {
        const groupName = this.groupByField.name;
        if (
            this.groupByField.type === "many2one" &&
            this.value &&
            groupName in this.model.tooltipInfo
        ) {
            this.tooltipKeepLast = this.tooltipKeepLast || new KeepLast();
            const resModel = this.groupByField.relation;
            const tooltipInfo = this.model.tooltipInfo[groupName];
            const fieldNames = Object.keys(tooltipInfo);
            // This read will be batched for all groups
            const [values] = await this.tooltipKeepLast.add(
                this.model.orm.silent.read(resModel, [this.value], ["display_name", ...fieldNames])
            );
            this.tooltip = fieldNames
                .filter((fieldName) => values[fieldName])
                .map((fieldName) => ({ title: tooltipInfo[fieldName], value: values[fieldName] }));
            this.model.notify();
        }
    }

    /**
     * Checks if the current active progress bar value contains records, and
     * deactivates it if not.
     * @returns {Promise<void>}
     */
    async checkActiveValue() {
        if (!this.hasActiveProgressValue) {
            return;
        }
        if (this.activeProgressBar.count === 0) {
            await this.filterProgressValue(null);
        }
    }

    async filterProgressValue(value) {
        this.progressValue.active = this.progressValue.active === value ? null : value;
        this.list.domain = this.getProgressBarDomain();

        // Do not update progress bars data when filtering on them.
        await Promise.all([this.list.load()]);
        this.model.trigger("group-updated", { group: this, withProgressBars: false });
    }

    /**
     * @param {Object} record
     * @returns {ProgressBar}
     */
    findProgressValueFromRecord(record) {
        const { fieldName } = this.model.progressAttributes;
        const value = record.data[fieldName];
        return (
            this.progressBars.find((pv) => pv.value === value) ||
            this.progressBars.find((pv) => pv.value === FALSE)
        );
    }

    /**
     * @override
     */
    getAggregates(fieldName) {
        if (!this.hasActiveProgressValue) {
            return super.getAggregates(...arguments);
        }
        return fieldName ? this.aggregates[fieldName] : this.activeProgressBar.count;
    }

    getProgressBarDomain() {
        const { fieldName } = this.model.progressAttributes;
        const domains = [this.groupDomain];
        if (this.hasActiveProgressValue) {
            if (this.progressValue.active === FALSE) {
                const values = this.progressBars
                    .map((pv) => pv.value)
                    .filter((val) => val !== this.progressValue.active);
                domains.push(["!", [fieldName, "in", values]]);
            } else {
                domains.push([[fieldName, "=", this.progressValue.active]]);
            }
        }
        return Domain.and(domains).toList();
    }

    updateAggregates(groupData) {
        const fname = this.groupByField.name;
        const { sumField } = this.model.progressAttributes;
        const group = groupData.find((g) => this.valueEquals(g[fname]));
        if (sumField) {
            this.aggregates[sumField.name] = group ? group[sumField.name] : 0;
        }
    }

    /**
     * @param {Object} [progressData]
     * @returns {Promise<void>}
     */
    async updateProgressData(progressData) {
        let value = this.displayName || this.value;
        if (value === true) {
            value = "True";
        } else if (value === false) {
            value = "False";
        }
        /** @type {Record<string, number>} */
        const groupProgressData = progressData[value] || {};
        /** @type {Map<string | symbol, number>} */
        const counts = new Map(
            groupProgressData ? Object.entries(groupProgressData) : [[FALSE, this.count]]
        );
        const total = [...counts.values()].reduce((acc, c) => acc + c, 0);
        counts.set(FALSE, this.count - total);
        for (const pv of this.progressBars) {
            pv.count = counts.get(pv.value) || 0;
        }
        await this.checkActiveValue();
    }

    /**
     * @param {number} index
     * @returns {Promise<Record | false>}
     */
    async validateQuickCreate() {
        const record = this.list.quickCreateRecord;
        let saved = false;
        if (record) {
            saved = await this.model.mutex.exec(async () => {
                const saved = await record._save({ noReload: true, stayInEdition: true });
                if (saved) {
                    this.count++;
                    if (record.parentActiveFields) {
                        record.setActiveFields(record.parentActiveFields);
                        record.parentActiveFields = false;
                    }
                    await this.model.reloadRecords(record);
                    record.switchMode("readonly");
                    this.addRecord(this.removeRecord(record), 0);
                }
                return saved;
            });
        }
        return saved ? record : false;
    }

    // ------------------------------------------------------------------------
    // Protected
    // ------------------------------------------------------------------------

    /**
     * @returns {ProgressBar[]}
     */
    _generateProgressBars() {
        if (!this.model.hasProgressBars) {
            return [];
        }
        const { colors, fieldName } = this.model.progressAttributes;
        const { selection: fieldSelection } = this.fields[fieldName];
        /** @type {[string | typeof FALSE, string][]} */
        const colorEntries = Object.entries(colors);
        const selection = fieldSelection && Object.fromEntries(fieldSelection);
        colorEntries.push([FALSE, "200"]);
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

export class KanbanDynamicGroupList extends DynamicGroupList {
    setup(params, state) {
        super.setup(...arguments);
        this.previousParams = state.previousParams || "[]";

        this.groupBy = this.groupBy.slice(0, 1);

        this.model.addEventListener("group-updated", async ({ detail }) => {
            if (this.groups.some((g) => g.id === detail.group.id)) {
                await this.updateGroupProgressData([detail.group], detail.withProgressBars);
                this.model.notify();
            }
        });
    }

    get sumFields() {
        const { sumField } = this.model.progressAttributes;
        return sumField ? [sumField.name] : [];
    }

    /**
     * @override
     */
    get fieldNames() {
        return [...super.fieldNames, ...this.sumFields];
    }

    get currentParams() {
        return JSON.stringify([this.domain, this.groupBy]);
    }

    exportState() {
        return {
            ...super.exportState(),
            previousParams: this.currentParams,
        };
    }

    /**
     * After a reload, empty groups are expcted to disappear from the web_read_group.
     * However, if the parameters are the same (domain + groupBy), we want to
     * temporarily keep these empty groups in the interface until the next reload
     * with different parameters.
     * @override
     */
    async load() {
        const load = async () => {
            const previousGroups = this.groups.map((g, i) => [g, i]);
            await super.load();
            if (this.previousParams === this.currentParams) {
                for (const [group, index] of previousGroups) {
                    const newGroup = this.groups.find((g) => group.valueEquals(g.value));
                    if (!group.deleted && !newGroup) {
                        group.empty();
                        this.groups.splice(index, 0, group);
                    }
                }
            }
        };
        await this._loadWithProgressData(load());
    }

    /**
     * @param {KanbanGroup[]} groups
     * @param {boolean} withProgressBars
     * @returns {Promise<void>}
     */
    async updateGroupProgressData(groups, withProgressBars) {
        if (!this.model.hasProgressBars) {
            return;
        }

        const gbFieldName = this.groupByField.name;
        const promises = {};

        if (withProgressBars) {
            const domain = Domain.or(groups.map((g) => g.groupDomain)).toList();
            promises.readProgressBar = this._fetchProgressData(domain);
        }
        // If we have a sumField, the aggregates must be re-fetched
        if (this.sumFields.length) {
            const domain = Domain.or(groups.map((g) => g.getProgressBarDomain())).toList();
            promises.webReadGroup = this.model.orm.webReadGroup(
                this.resModel,
                domain,
                this.sumFields,
                this.groupBy,
                { lazy: true }
            );
        }

        await Promise.all(Object.values(promises));

        // Update the aggregates for each group
        if (promises.webReadGroup) {
            const result = await promises.webReadGroup;
            const groupData = result.groups.map((group) => ({
                ...group,
                [gbFieldName]: this._getValueFromGroupData(group, this.firstGroupBy),
            }));
            for (const group of groups) {
                group.updateAggregates(groupData);
            }
        }
        // Update the progress bar data for each group
        if (promises.readProgressBar) {
            const result = await promises.readProgressBar;
            await Promise.all(groups.map((group) => group.updateProgressData(result)));
        }
    }

    /**
     * @param {string} dataRecordId
     * @param {string} dataGroupId
     * @param {string} refId
     * @param {string} targetGroupId
     */
    async moveRecord(dataRecordId, dataGroupId, refId, targetGroupId) {
        const sourceGroup = this.groups.find((g) => g.id === dataGroupId);
        const targetGroup = this.groups.find((g) => g.id === targetGroupId);

        if (!sourceGroup || !targetGroup) {
            return; // Groups have been re-rendered, old ids are ignored
        }

        const record = sourceGroup.list.records.find((r) => r.id === dataRecordId);

        try {
            this.model.transaction.start(dataRecordId);
        } catch (err) {
            if (err instanceof TransactionInProgress) {
                return;
            }
            throw err;
        }

        // Move from one group to another
        const fullyLoadGroup = targetGroup.isFolded;
        if (dataGroupId !== targetGroupId) {
            const refIndex = targetGroup.list.records.findIndex((r) => r.id === refId);
            // Quick update: moves the record at the right position and notifies components
            targetGroup.addRecord(sourceGroup.removeRecord(record), refIndex + 1);
            const value = isRelational(this.groupByField)
                ? [targetGroup.value, targetGroup.displayName]
                : targetGroup.value;

            const abort = () => {
                this.model.transaction.abort(dataRecordId);
                this.model.notify();
            };

            try {
                await record.update({ [this.groupByField.name]: value });
                const saved = await record.save({ noReload: true });
                if (!saved) {
                    abort();
                    return;
                }
            } catch (err) {
                abort();
                throw err;
            }

            const promises = [this.updateGroupProgressData([sourceGroup, targetGroup], true)];
            if (fullyLoadGroup) {
                // The group is folded: we need to load it
                // In this case since we load after saving the record there is no
                // need to reload the record nor to resequence the list.
                promises.push(targetGroup.toggle());
            } else {
                // Record can be loaded along with the group metadata
                promises.push(record.load());
            }

            await Promise.all(promises);
        }

        if (fullyLoadGroup) {
            this.model.notify();
        } else {
            // Only trigger resequence if the group hasn't been fully loaded
            await targetGroup.list.resequence(dataRecordId, refId);
        }

        this.model.transaction.commit(dataRecordId);

        return true;
    }

    // ------------------------------------------------------------------------
    // Protected
    // ------------------------------------------------------------------------

    /**
     * @param {any[]} [domain]
     * @returns {Promise<Object>}
     */
    async _fetchProgressData(domain) {
        const { colors, fieldName, help } = this.model.progressAttributes;
        return this.model.orm.call(this.resModel, "read_progress_bar", [], {
            domain,
            group_by: this.firstGroupBy,
            progress_bar: { colors, field: fieldName, help },
            context: this.context,
        });
    }

    /**
     * @param {Promise<any>} loadPromise
     * @returns {Promise<void>}
     */
    async _loadWithProgressData(loadPromise) {
        if (!this.model.hasProgressBars) {
            // No progress attributes : normal load
            return loadPromise;
        }
        const [progressData] = await Promise.all([
            this._fetchProgressData(this.domain),
            loadPromise,
        ]);
        await Promise.all(this.groups.map((group) => group.updateProgressData(progressData)));
    }
}

export class KanbanDynamicRecordList extends DynamicRecordList {
    async moveRecord(dataRecordId, _dataGroupId, refId) {
        this.model.transaction.start(dataRecordId);

        try {
            await this.resequence(dataRecordId, refId);
        } catch (err) {
            this.model.transaction.abort(dataRecordId);
            this.model.notify();
            throw err;
        }

        this.model.transaction.commit(dataRecordId);
    }
}

KanbanDynamicRecordList.DEFAULT_LIMIT = 40;

export class KanbanModel extends RelationalModel {
    setup(params) {
        super.setup(...arguments);

        this.progressAttributes = params.progressAttributes;
        this.tooltipInfo = params.tooltipInfo;
        this.transaction = makeTransactionManager();
    }

    get hasProgressBars() {
        return Boolean(this.progressAttributes);
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
            return this.root.groups.some(
                (group) => group.count > 0 || group.list.quickCreateRecord
            );
        }
        return this.root.records.length > 0;
    }
}

KanbanModel.DynamicGroupList = KanbanDynamicGroupList;
KanbanModel.DynamicRecordList = KanbanDynamicRecordList;
KanbanModel.Group = KanbanGroup;
