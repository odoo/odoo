/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { isRelational } from "@web/views/helpers/view_utils";
import { DynamicGroupList, DynamicRecordList, RelationalModel } from "@web/views/relational_model";

const FALSE_SYMBOL = Symbol.for("false");

class KanbanDynamicGroupList extends DynamicGroupList {
    /**
     * @override
     */
    async load() {
        const promises = [super.load()];
        if (this.model.progress && this.groupBy && this.groupBy.length) {
            promises.push(this._fetchProgressData(this));
        }
        const [, progressData] = await Promise.all(promises);

        if (progressData) {
            this._populateProgressData(progressData);
        }
    }

    async _fetchProgressData() {
        return this.model.orm.call(this.resModel, "read_progress_bar", [], {
            domain: this.domain,
            group_by: this.groupBy[0],
            progress_bar: {
                colors: this.model.progress.colors,
                field: this.model.progress.fieldName,
                help: this.model.progress.help,
                sum_field: this.model.progress.sumField,
            },
            context: this.context,
        });
    }

    _populateProgressData(progressData) {
        const { fieldName, colors } = this.model.progress;
        const progressField = this.fields[fieldName];
        const colorEntries = Object.entries(colors);
        const selection = Object.fromEntries(progressField.selection || []);

        let mutedEntry = colorEntries.find((e) => e[1] === "muted");
        if (!mutedEntry) {
            mutedEntry = [FALSE_SYMBOL, "muted"];
            colorEntries.push(mutedEntry);
            selection[FALSE_SYMBOL] = this.model.env._t("Other");
        }

        for (const group of this.groups) {
            const total = group.count;
            const values = progressData[group.displayName || group.value] || {
                [FALSE_SYMBOL]: total,
            };
            const count = Object.values(values).reduce((acc, x) => acc + x, 0) || total;

            group.progress = [];

            for (const [key, color] of colorEntries) {
                group.progress.push({
                    count: key in values ? values[key] : total - count,
                    total,
                    value: key,
                    string: key in selection ? selection[key] : key,
                    color,
                });
            }
        }
    }

    async filterProgressValue(group, value) {
        const { fieldName } = this.model.progress;
        group.activeProgressValue = group.activeProgressValue === value ? null : value;
        let progressBarDomain;
        if (group.activeProgressValue) {
            const val = group.activeProgressValue;
            progressBarDomain = [[fieldName, "=", val === FALSE_SYMBOL ? false : val]];
        }
        group.list.domain = Domain.and([
            group.domain,
            group.groupDomain,
            progressBarDomain,
        ]).toList();

        await group.load();
        this.model.notify();
    }

    async moveRecord(dataRecordId, dataListId, refId, newListId) {
        const { list } = this.groups.find((g) => g.id === dataListId);
        const { list: newList, value: newValue } = this.groups.find((g) => g.id === newListId);
        const record = list.records.find((r) => r.id === dataRecordId);

        // Quick update: moves the record at the right position and notifies components
        list.records = list.records.filter((r) => r !== record);
        list.count--;
        if (!newList.isFolded) {
            const index = refId ? newList.records.findIndex((r) => r.id === refId) + 1 : 0;
            newList.records.splice(index, 0, record);
        }
        newList.count++;
        this.model.notify();

        // move from one group to another
        if (dataListId !== newListId) {
            const value = isRelational(this.groupByField) ? [newValue] : newValue;
            await record.update(this.groupByField.name, value);
            await record.save();
            await this.load();
        }
        await newList.resequence();
    }
}

class KanbanDynamicRecordList extends DynamicRecordList {
    async archive() {
        const resIds = this.records.map((r) => r.resId);
        await this.model.orm.call(this.resModel, "action_archive", [resIds]);
        await this.model.load();
    }

    async unarchive() {
        const resIds = this.records.map((r) => r.resId);
        await this.model.orm.call(this.resModel, "action_unarchive", [resIds]);
        await this.model.load();
    }
}

export class KanbanModel extends RelationalModel {
    setup(params = {}) {
        super.setup(...arguments);

        this.progress = params.progress;
        this.defaultGroupBy = params.defaultGroupBy || false;
    }

    /**
     * Applies the default groupBy defined on the arch when not in a dialog.
     * @override
     */
    async load(params = {}) {
        const actualParams = { ...params };
        if (this.defaultGroupBy && !this.env.inDialog) {
            const groupBy = [...(this.groupBy || []), this.defaultGroupBy];
            actualParams.groupBy = groupBy.slice(0, 1);
        }
        await super.load(actualParams);
    }
}

KanbanModel.DynamicGroupList = KanbanDynamicGroupList;
KanbanModel.DynamicRecordList = KanbanDynamicRecordList;
