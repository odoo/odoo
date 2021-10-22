/** @odoo-module **/

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
            promises.push(this.fetchProgressData(actualParams));
        }

        const [, progressData] = await Promise.all(promises);

        if (progressData) {
            this.populateProgressData(progressData);
        }
    }

    async fetchProgressData({ context, domain, groupBy }) {
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

        if (!colorEntries.some((e) => e[1] === "muted")) {
            colorEntries.push([FALSE_SYMBOL, "muted"]);
            selection[FALSE_SYMBOL] = this.env._t("Other");
        }

        for (const group of this.root.data) {
            const values = progressData[group.displayName || group.value] || {};
            const total = group.count;
            const count = Object.values(values).reduce((acc, x) => acc + x, 0);

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
}
