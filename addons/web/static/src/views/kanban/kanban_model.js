/** @odoo-module **/

import { RelationalModel } from "@web/views/relational_model";
import { Domain } from "@web/core/domain";

const FALSE_SYMBOL = Symbol.for("false");

export class KanbanModel extends RelationalModel {
    setup(params = {}) {
        super.setup(...arguments);

        this.progress = Object.assign({}, params.progress, { data: {} });
        this.defaultGroupBy = params.defaultGroupBy || false;
    }

    /**
     * Applies the default groupBy defined on the arch when not in a dialog.
     * @override
     */
    async load(params = {}) {
        const groupBy = params.groupBy.slice();
        if (this.defaultGroupBy && !this.env.inDialog) {
            groupBy.push(this.defaultGroupBy);
        }
        const actualParams = { ...params, groupBy: groupBy.slice(0, 1) };
        const loadProgress = this.progress && actualParams.groupBy.length;
        const promises = [super.load(actualParams)];
        if (loadProgress) {
            promises.push(this.fetchProgressData(actualParams));
        }

        await Promise.all(promises);

        if (loadProgress) {
            this.populateProgressData();
        }
    }

    async fetchProgressData({ domain, groupBy, context }) {
        const progress_bar = {
            colors: this.progress.colors,
            field: this.progress.fieldName,
            help: this.progress.help,
            sum_field: this.progress.sumField,
        };
        this.progress.data = await this.orm.call(this.resModel, "read_progress_bar", [], {
            domain,
            group_by: groupBy[0],
            progress_bar,
            context,
        });
    }

    populateProgressData() {
        const progressField = this.root.fields[this.progress.fieldName];
        const colorEntries = Object.entries(this.progress.colors);
        const selection = Object.fromEntries(progressField.selection || []);

        if (!colorEntries.some((e) => e[1] === "muted")) {
            colorEntries.push([FALSE_SYMBOL, "muted"]);
            selection[FALSE_SYMBOL] = this.env._t("Other");
        }

        for (const group of this.root.data) {
            const values = this.progress.data[group.displayName || group.value] || {};
            const total = group.count;
            const count = Object.values(values).reduce((acc, x) => acc + x, 0);

            group.activeProgressValue = null;
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
        const domains = [group.domain];
        group.activeProgressValue = group.activeProgressValue === value ? null : value;
        if (group.activeProgressValue) {
            const val = group.activeProgressValue;
            domains.push([[fieldName, "=", val === FALSE_SYMBOL ? false : val]]);
        }

        group.domain = Domain.and(domains).toList();

        await group.load();

        group.domain = domains[0];
        this.notify();
    }
}
