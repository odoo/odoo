import { PivotModel } from "@web/views/pivot/pivot_model";

export class SkillsPivotModel extends PivotModel {
    setup() {
        super.setup(...arguments);
        this.departmentsFetch = false;
        this.departmentNamesById = {};
    }

    async _getGroupsSubdivision(params, groupInfo) {
        if (!this.departmentsFetch) {
            const departmentNames = await this.orm.webSearchRead("hr.department", [], {
                specification: {
                    name: {},
                },
            });
            this.departmentNamesById = Object.fromEntries(
                departmentNames.records.map(({ id, name }) => [id, name])
            );
        }
        const multiData = await super._getGroupsSubdivision(...arguments);

        for (const [groupBy, data] of params.groupingSets.map((g, i) => [g, multiData[i]])) {
            if (groupBy.includes("department_id")) {
                data.subGroups.forEach((res) => {
                    res.department_id[1] = this.departmentNamesById[res.department_id[0]];
                });
            }
        }
        return multiData;
    }
}
