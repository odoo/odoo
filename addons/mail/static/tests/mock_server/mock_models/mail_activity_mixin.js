import { fields } from "@web/../tests/web_test_helpers";

export function makeMailActivityMixin(modelClass) {
    return class extends modelClass {
        activity_type_id = fields.Many2one({
            relation: "mail.activity.type",
            string: "Next Activity Type",
            compute: "_compute_activity_type_id",
        });

        _compute_activity_type_id() {
            for (const record of this) {
                const activities =
                    record.activity_ids?.filter((activity) => {
                        const activityRecord = this.env["mail.activity"].browse(activity)[0];
                        return activityRecord?.state !== "done";
                    }) || [];

                if (activities.length > 0) {
                    const activityRecords = this.env["mail.activity"].browse(activities);
                    const firstActivity = activityRecords.reduce((earliest, current) => {
                        const earliestDate = earliest.date_deadline || "9999-12-31";
                        const currentDate = current.date_deadline || "9999-12-31";
                        return currentDate < earliestDate ? current : earliest;
                    });
                    record.activity_type_id = firstActivity.activity_type_id;
                } else {
                    record.activity_type_id = false;
                }
            }
        }
    };
}
