import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";
import { onActivityChangedType } from "@mail/core/web/activity_types";
import { propComputed } from "@mail/utils/common/hooks";
import { compareDatetime } from "@mail/utils/common/misc";

import { Component, computed, signal, types, useOnChange, useProps } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class ActivityListPopover extends Component {
    static components = { ActivityListPopoverItem };
    static template = "mail.ActivityListPopover";

    rootRef = signal.ref();

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.activityIds = propComputed("activityIds", types.array(types.number()));
        this.close = useProps.static("close", types.function([]));
        this.defaultActivityTypeId = propComputed(
            "defaultActivityTypeId",
            types.number().optional()
        );
        this.onActivityChanged = useProps.static(
            "onActivityChanged",
            onActivityChangedType(this.store)
        );
        this.resId = propComputed("resId", types.number());
        /** Ids of record selection used to schedule activities in batch; it must include resId. */
        this.resIds = propComputed("resIds", types.array(types.number()).optional());
        this.resModel = propComputed("resModel", types.string());
        this.thread = computed(() =>
            this.store["mail.thread"].insert({
                model: this.resModel(),
                id: this.resId(),
            })
        );
        useOnChange(
            () => [this.activityIds()],
            (activityIds) => this.store.fetchStoreData("mail.activity", { ids: activityIds })
        );
    }

    get activities() {
        /** @type {import("models").Activity[]} */
        const allActivities = Object.values(this.store["mail.activity"].records);
        return allActivities
            .filter((activity) => this.activityIds().includes(activity.id))
            .sort((a, b) => compareDatetime(a.date_deadline, b.date_deadline) || a.id - b.id);
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ threadAtRender: import("models").Thread }} param1
     */
    onClickAddActivityButton(ev, { threadAtRender }) {
        this.store
            .scheduleActivity(
                threadAtRender.model,
                this.resIds() ? this.resIds() : [threadAtRender.id],
                this.defaultActivityTypeId()
            )
            .then(() => this.onActivityChanged({ thread: threadAtRender }));
        this.close();
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
