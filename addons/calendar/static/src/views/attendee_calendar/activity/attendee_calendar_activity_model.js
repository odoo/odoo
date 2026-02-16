import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { deserializeDate } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
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
     * User pending activities data.
     */
    get activities() {
        return this.data.activities;
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
     * Create a Full Calendar library event with the activities for the day.
     */
    createActivityEventAt(day, activities) {
        const event = {
            id: `activity-event-${day.toISODate()}`,
            colorIndex: user.partnerId || 0,
            duration: 1,
            start: day,
            // "end" needed even for all day events to represent it on the calendar.
            end: day.plus({ hours: 1 }),
            isActivity: true,
            isAllDay: true,
            resModel: "mail.activity",
            rawRecord: activities,
        };
        if (this.env.isSmall) {
            event.title = activities.length;
        } else if (activities.length > 1) {
            event.title = _t("%s pending activities", activities.length);
        } else {
            event.title = activities[0].display_name;
        }
        return event;
    },

    /**
     * Update the model activity data with the user pending activities.
     */
    async updateActivityData(data) {
        if (!this.userActivitiesEnabled) {
            data.activities = {};
            return;
        }
        // Retrieves user pending activities
        const activities = await this.orm.webSearchRead(
            "mail.activity",
            [
                ["active", "=", true], // Done activities are archived
                ["user_id", "=", user.userId],
            ],
            {
                limit: 1000, // Same default limit as systray activities
                specification: {
                    date_deadline: {},
                    display_name: {},
                },
            }
        );
        if (!activities.length) {
            data.activities = {};
            return;
        }
        // Create activity events
        const activitiesPerDueDate = activities.records.reduce((acc, activity) => {
            const key = activity.date_deadline;
            if (!acc[key]) {
                acc[key] = [];
            }
            acc[key].push(activity);
            return acc;
        }, {});
        const activityEvents = {};
        for (const [date, activities] of Object.entries(activitiesPerDueDate)) {
            const activityEvent = this.createActivityEventAt(deserializeDate(date), activities);
            activityEvents[activityEvent.id] = activityEvent;
        }
        data.activities = activityEvents;
    },

    /**
     * @override
     */
    async updateData(data) {
        await super.updateData(...arguments);
        await this.updateActivityData(data);
    },
});
