import { SearchModel } from "@web/search/search_model";
import { user } from "@web/core/user";

export class TimeOffReportCalendarSearchModel extends SearchModel {
    async load(config) {
        const publicEmployees = await this.orm.searchRead(
            "hr.employee.public",
            [],
            ["child_ids", "user_id"],
        );

        if (publicEmployees.length < 50) {
            return super.load(config);
        }

        const currentEmployee = publicEmployees.find((emp) => emp.user_id[0] === user.userId);
        const hasSubordinates = currentEmployee?.child_ids?.length > 0;

        return super.load({
            ...config,
            context: {
                ...config.context,
                search_default_my_team: Number(hasSubordinates),
                search_default_department: Number(!hasSubordinates),
            },
        });
    }
}
