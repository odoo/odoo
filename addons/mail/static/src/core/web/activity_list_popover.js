import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";
import { useOnChange } from "@mail/utils/common/hooks";
import { compareDatetime } from "@mail/utils/common/misc";

import { Component, props, types } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class ActivityListPopover extends Component {
    static components = { ActivityListPopoverItem };
    static template = "mail.ActivityListPopover";

    setup() {
        super.setup();
        this.props = props({
            activityIds: types.array(types.number()),
            close: types.function([]),
            defaultActivityTypeId: types.number().optional(),
            onActivityChanged: types.function([]),
            resId: types.number(),
            /** Ids of record selection used to schedule activities in batch; it must include resId. */
            resIds: types.array(types.number()).optional(),
            resModel: types.string(),
        });
        this.store = useService("mail.store");
        useOnChange(
            () => [this.props.activityIds],
            (activityIds) => this.store.fetchStoreData("mail.activity", { ids: activityIds })
        );
    }

    get activities() {
        /** @type {import("models").Activity[]} */
        const allActivities = Object.values(this.store["mail.activity"].records);
        return allActivities
            .filter((activity) => this.props.activityIds.includes(activity.id))
            .sort((a, b) => compareDatetime(a.date_deadline, b.date_deadline) || a.id - b.id);
    }

    onClickAddActivityButton() {
        this.store
            .scheduleActivity(
                this.props.resModel,
                this.props.resIds ? this.props.resIds : [this.props.resId],
                this.props.defaultActivityTypeId
            )
            .then(() => this.props.onActivityChanged());
        this.props.close();
    }

    get doneActivities() {
        return this.activities.filter((activity) => activity.state === "done");
    }

    get overdueActivities() {
        return this.activities.filter((activity) => activity.state === "overdue");
    }

    get plannedActivities() {
        return this.activities.filter((activity) => activity.state === "planned");
    }

    get todayActivities() {
        return this.activities.filter((activity) => activity.state === "today");
    }
}
