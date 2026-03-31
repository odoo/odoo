import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { deserializeDate, serializeDate } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

/**
 * Load the pending user activities in the Attendee Calendar model.
 * Can be activated/deactivated using the "userActivitiesEnabled" getter.
 *
 * Done using a patch to prevent loading this feature and its mail components/store service in POS
 * (only POS module concerned/using the attendee calendar view : 'pos_appointment').
 */
patch(AttendeeCalendarModel.prototype, {
    /**
     * User pending activities structured as full calendar library events for rendering.
     */
    get activityEvents() {
        return this.data.activityEvents;
    },

    /**
     * Whether or not to show the activities in the attendee calendar.
     * User preference controlled using a filter in the calendar side bar.
     */
    get showActivities() {
        return user.settings.calendar_show_activities;
    },

    /**
     * Override to control whether or not the current user can see and manage
     * their activities directly from the attendee calendar.
     * Activate/Deactivate the feature.
     **/
    get userActivitiesEnabled() {
        return true;
    },

    /**
     * Initialize a Full Calendar library event from an activity record.
     */
    normalizeActivityEventRecord(activity) {
        return {
            id: `activity-event-${activity.id}`,
            activityId: activity.id,
            titleIcon: "fa fa-clock-o",
            title: activity.display_name,
            colorIndex: user.partnerId || 0,
            duration: 1,
            start: deserializeDate(activity.date_deadline),
            // "end" needed even for all day events to represent it on the calendar.
            end: deserializeDate(activity.date_deadline).plus({ hours: 1 }),
            isActivity: true,
            isAllDay: true,
            resModel: "mail.activity",
        };
    },

    /**
     * Retrieves the user’s pending activities.
     * Structures them as full calendar library events to be rendered on the calendar view,
     * and saves them in the store to render their associated activity popover.
     */
    async updateActivityData(data) {
        if (!this.userActivitiesEnabled || !this.showActivities || this.meta.scale === "year") {
            data.activityEvents = {};
            return;
        }
        // Retrieves user pending activities for the current calendar date range
        // Done activities are archived and therefore excluded by default.
        const activities = await this.orm.webSearchRead(
            "mail.activity",
            [
                ["date_deadline", ">=", serializeDate(data.range.start)],
                ["date_deadline", "<=", serializeDate(data.range.end)],
                ["user_id", "=", user.userId],
            ],
            {
                specification: {
                    date_deadline: {},
                    display_name: {},
                },
            }
        );
        if (!activities.length) {
            data.activityEvents = {};
            return;
        }
        const activityEvents = {};
        for (const activity of activities.records) {
            const activityEvent = this.normalizeActivityEventRecord(activity);
            activityEvents[activityEvent.id] = activityEvent;
        }
        // Add the activity events in the model data for calendar view rendering.
        data.activityEvents = activityEvents;
        // Insert the activity records in the store for activity popover rendering.
        const storeData = await this.orm.silent.call("mail.activity", "activity_format", [
            activities.records.map((a) => a.id),
        ]);
        this.env.services["mail.store"].insert(storeData);
    },

    /**
     * @override
     */
    async updateData(data) {
        await super.updateData(...arguments);
        await this.updateActivityData(data);
    },
});
