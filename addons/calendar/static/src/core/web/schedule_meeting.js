/**
 * Books a meeting from its slot: the calendar opens, and the quick create of the slot picked
 * there comes prefilled with a Discuss video call. Saving it brings the user back to where
 * they scheduled from, `CalendarQuickCreateFormController` taking care of the return.
 */
export async function openScheduleMeeting(env) {
    const videocallLocation = await env.services.orm.call(
        "calendar.event",
        "get_discuss_videocall_location"
    );
    await env.services.action.doAction("calendar.action_calendar_event", {
        additionalContext: {
            default_access_token: videocallLocation.split("/").pop(),
            default_videocall_location: videocallLocation,
            disable_event_creation_as_draft: true,
            return_to_parent_breadcrumb: true,
        },
    });
}
