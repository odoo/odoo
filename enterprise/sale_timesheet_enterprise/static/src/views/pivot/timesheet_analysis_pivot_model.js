import { _t } from "@web/core/l10n/translation";

import { PivotModel } from "@web/views/pivot/pivot_model";

export class TimesheetAnalysisPivotModel extends PivotModel {
    setup(params) {
        super.setup(...arguments);
        this.targets = {};
        this.targetsFetched = false;
    }

    async _getSubGroups(groupBy, params) {
        const data = await super._getSubGroups(...arguments);

        if (!this.targetsFetched) {
            const targets = await this.orm.call("hr.employee", "get_all_billable_time_targets");
            this.targets = Object.fromEntries(
                targets.map(({ id, billable_time_target }) => [id, billable_time_target])
            );
            this.targetsFetched = true;
        }

        if (groupBy.includes("employee_id")) {
            data.forEach((res) => {
                const target = this.targets[res.employee_id[0]];
                if (target) {
                    const name = _t("%(employee_name)s (%(target)sh / month)", {
                        employee_name: res.employee_id[1],
                        target: target,
                    });
                    res.employee_id[1] = name;
                }
            });
        }

        return data;
    }
}
