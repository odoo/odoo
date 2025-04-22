import { PivotModel } from "@web/views/pivot/pivot_model";


export class SkillsPivotModel extends PivotModel {
    setup() {
        super.setup(...arguments);
        this.departmentsFetch = false;
        this.departmentNamesById = {};
    }

    async _getSubGroups(groupBy, params) {
        if (!this.departmentsFetch){
            const departmentNames = await this.orm.webSearchRead(
                "hr.department",
                [],
                {
                    specification: {
                        name: {},
                    },
                }
            );
            this.departmentNamesById = Object.fromEntries(
                departmentNames.records.map(({ id, name }) => [id, name])
            );
        }
        const data = await super._getSubGroups(...arguments);
        if (groupBy.includes("department_id")) {
            data.forEach((res) => {
                res.department_id[1] = this.departmentNamesById[res.department_id[0]];
            });
        }

        return data;
    }
}
