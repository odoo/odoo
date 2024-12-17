import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class WebsiteEventMeetingRoom extends Interaction {
    static selector = ".o_wevent_meeting_room_card";
    dynamicContent = {
        '.o_wevent_meeting_room_delete': { "t-on-click.prevent.stop": this.onClickDelete },
        '.o_wevent_meeting_room_duplicate': { "t-on-click.prevent.stop": this.onClickDuplicate },
        '.o_wevent_meeting_room_is_pinned': { "t-on-click.prevent.stop": this.onClickIsPinned },
    }

    setup() {
        this.meetingRoomId = parseInt(this.el.dataset["meetingRoomId"]);
    }

    onClickDelete() {
        this.services.dialog.add(ConfirmationDialog, {
            body: _t("Are you sure you want to close this room?"),
            confirm: async () => {
                await this.waitFor(this.services.orm.write(
                    "event.meeting.room",
                    [this.meetingRoomId],
                    { is_published: false },
                    { context: user.context } // this.services.user.context
                ));

                // remove the element so we do not need to refresh the page
                this.el.remove();
            },
        })
    }

    onClickDuplicate() {
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

    async onClickIsPinned(ev) {
        const target = ev.currentTarget
        const pinnedButtonClass = "o_wevent_meeting_room_pinned";
        const isPinned = ev.currentTarget.classList.contains(pinnedButtonClass);

        await this.waitFor(this.services.orm.write(
            "event.meeting.room",
            [this.meetingRoomId],
            { is_pinned: !isPinned },
            { context: user.context }
        ));

        target.classList.toggle(pinnedButtonClass, !isPinned);
    }
}

registry
    .category("public.interactions")
    .add("website_event_meet.website_event_meeting_room", WebsiteEventMeetingRoom);
