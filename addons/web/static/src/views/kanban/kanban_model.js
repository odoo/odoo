/** @odoo-module **/

import {
    DynamicGroupList,
    DynamicRecordList,
    Group,
    RelationalModel,
} from "@web/views/relational_model";
import { isRelational } from "@web/views/utils";

import { EventBus } from "@odoo/owl";

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

        this.tooltip = [];

        this.model.transaction.register({
            onStart: () => ({
                count: this.count,
                records: [...this.list.records],
            }),
            onAbort: ({ count, records }) => {
                this.count = count;
                this.list.records = records;
            },
        });
    }
}

export class KanbanDynamicGroupList extends DynamicGroupList {
    setup(params, state) {
        super.setup(...arguments);
        this.previousParams = state.previousParams || "[]";

        this.groupBy = this.groupBy.slice(0, 1);
        this.limit = null;
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
        await super.load();
        if (this.previousParams === this.currentParams) {
            this.previousGroupsStates.forEach((groupState, index) => {
                const groupDisapeared = !this.groups.find((g) => g.valueEquals(groupState.value));
                if (!groupState.deleted && groupDisapeared) {
                    const { value, displayName, __rawValue, isFolded, groupDomain, range } = groupState;
                    const group = this.model.createDataPoint("group", {
                        ...this.commonGroupParams,
                        count: 0,
                        value,
                        displayName,
                        __rawValue,
                        aggregates: {},
                        groupByField: this.groupByField,
                        groupDomain,
                        isFolded,
                        range,
                        rawContext: this.rawContext,
                    });
                    this.groups.splice(index, 0, group);
                }
            });
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
                await record.update({ [this.groupByField.name]: value }, { silent: true });
                const saved = await record.save({ noReload: true });
                if (!saved) {
                    abort();
                    this.model.notify();
                    return;
                }
            } catch (err) {
                abort();
                throw err;
            }

            const promises = [];
            const groupsToReload = [sourceGroup];
            if (!targetGroup.isFolded) {
                groupsToReload.push(targetGroup);
                promises.push(record.load());
            }
            await Promise.all(promises);
        }

        if (!targetGroup.isFolded) {
            // Only trigger resequence if the group isn't folded
            await targetGroup.list.resequence(dataRecordId, refId);
        }
        this.model.notify();

        this.model.transaction.commit(dataRecordId);

        return true;
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

        this.transaction = makeTransactionManager();
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
            return this.root.groups.some((group) => group.count > 0);
        }
        return this.root.records.length > 0;
    }
}

KanbanModel.DynamicGroupList = KanbanDynamicGroupList;
KanbanModel.DynamicRecordList = KanbanDynamicRecordList;
KanbanModel.Group = KanbanGroup;
