import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

export class MeetingRoom extends Interaction {
    static selector = ".o_wevent_meeting_room_card";
    dynamicContent = {
        ".o_wevent_meeting_room_delete": { "t-on-click.prevent.stop": this.onDeleteRoomClick },
        ".o_wevent_meeting_room_duplicate": { "t-on-click.prevent.stop": this.onDuplicateRoomClick },
        ".o_wevent_meeting_room_is_pinned": { "t-on-click.prevent.stop.withTarget": this.onTogglePinnedClick },
    };

    setup() {
        this.meetingRoomId = parseInt(this.el.dataset["meetingRoomId"]);
    }

    onDeleteRoomClick() {
        this.services.dialog.add(ConfirmationDialog, {
            body: _t("Are you sure you want to close this room?"),
            confirm: async () => {
                await this.waitFor(this.services.orm.write(
                    "event.meeting.room",
                    [this.meetingRoomId],
                    { is_published: false },
                    { context: user.context }, // this.services.user.context
                ));

                // remove the element so we do not need to refresh the page
                this.el.remove();
            },
        })
    }

    onDuplicateRoomClick() {
        this.services.dialog.add(ConfirmationDialog, {
            body: _t("Are you sure you want to duplicate this room?"),
            confirm: async () => {
                await this.waitFor(this.services.orm.call("event.meeting.room", "copy", [this.meetingRoomId], {
                    context: user.context,
                }));

                window.location.reload();
            },
        });
    }

    async onTogglePinnedClick(ev, currentTargetEl) {
        const wasPinned = currentTargetEl.classList.contains("o_wevent_meeting_room_pinned");

        await this.waitFor(this.services.orm.write(
            "event.meeting.room",
            [this.meetingRoomId],
            { is_pinned: !wasPinned },
            { context: user.context },
        ));

        currentTargetEl.classList.toggle("o_wevent_meeting_room_pinned", !wasPinned);
    }
}

registry
    .category("public.interactions")
    .add("website_event_meet.meeting_room", MeetingRoom);
