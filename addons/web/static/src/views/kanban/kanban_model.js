/** @odoo-module **/

import { isRelational } from "@web/views/helpers/view_utils";
import { RelationalModel } from "@web/views/relational_model";

const FALSE_SYMBOL = Symbol.for("false");

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
        if (params.groupBy) {
            const groupBy = (params.groupBy || []).slice();
            if (this.defaultGroupBy && !this.env.inDialog) {
                groupBy.push(this.defaultGroupBy);
            }
            actualParams.groupBy = groupBy.slice(0, 1);
        }
        const promises = [super.load(actualParams)];
        if (this.progress && actualParams.groupBy && actualParams.groupBy.length) {
            this.progressSearchParams = actualParams;
            promises.push(this.fetchProgressData(actualParams));
        }

        const [, progressData] = await Promise.all(promises);

        if (progressData) {
            this.populateProgressData(progressData);
        }
    }

    async fetchProgressData() {
        const { context, domain, groupBy } = this.progressSearchParams;
        return this.orm.call(this.resModel, "read_progress_bar", [], {
            domain,
            group_by: groupBy[0],
            progress_bar: {
                colors: this.progress.colors,
                field: this.progress.fieldName,
                help: this.progress.help,
                sum_field: this.progress.sumField,
            },
            context,
        });
    }

    populateProgressData(progressData) {
        const progressField = this.root.fields[this.progress.fieldName];
        const colorEntries = Object.entries(this.progress.colors);
        const selection = Object.fromEntries(progressField.selection || []);

        let mutedEntry = colorEntries.find((e) => e[1] === "muted");
        if (!mutedEntry) {
            mutedEntry = [FALSE_SYMBOL, "muted"];
            colorEntries.push(mutedEntry);
            selection[FALSE_SYMBOL] = this.env._t("Other");
        }

        for (const group of this.root.data) {
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
        const { fieldName } = this.progress;
        group.activeProgressValue = group.activeProgressValue === value ? null : value;
        if (group.activeProgressValue) {
            const val = group.activeProgressValue;
            group.domains.progress = [[fieldName, "=", val === FALSE_SYMBOL ? false : val]];
        } else {
            delete group.domains.progress;
        }

        await group.load();
        this.notify();
    }

    async moveRecord(dataRecordId, dataListId, refId, newListId) {
        const record = this.db[dataRecordId];
        const list = this.db[dataListId];
        const newList = this.db[newListId];

        // Quick update: moves the record at the right position and notifies components
        list.data = list.data.filter((r) => r !== record);
        list.count--;
        if (newList.isLoaded) {
            const index = refId ? newList.data.findIndex((r) => r.id === refId) + 1 : 0;
            newList.data.splice(index, 0, record);
        }
        newList.count++;
        this.notify();

        // Actual processing
        if (dataListId !== newListId) {
            const { groupByField } = this.root;
            const value = isRelational(groupByField) ? [newList.value] : newList.value;
            await record.update(groupByField.name, value);
            await record.save();
            const promises = [this.load({ keepRecords: true })];
            if (this.progress) {
                promises.push(this.fetchProgressData());
            }
            const [, progressData] = await Promise.all(promises);
            if (progressData) {
                this.populateProgressData(progressData);
            }
        }
        await newList.resequence();
    }
}
