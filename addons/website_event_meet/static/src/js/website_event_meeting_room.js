/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";

publicWidget.registry.websiteEventMeetingRoom = publicWidget.Widget.extend({
    selector: '.o_wevent_meeting_room_card',
    events: {
        'click .o_wevent_meeting_room_delete': '_onDeleteClick',
        'click .o_wevent_meeting_room_duplicate': '_onDuplicateClick',
        'click .o_wevent_meeting_room_is_pinned': '_onPinClick',
    },

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    start: function () {
        this._super.apply(this, arguments);
        this.meetingRoomId = parseInt(this.el.dataset["meetingRoomId"]);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
      * Delete the meeting room.
      *
      * @private
      */
    _onDeleteClick: async function (event) {
        event.preventDefault();
        event.stopPropagation();

        this.call("dialog", "add", ConfirmationDialog, {
            body: _t("Are you sure you want to close this room?"),
            confirm: async () => {
                await this.orm.write(
                    "event.meeting.room",
                    [this.meetingRoomId],
                    { is_published: false },
                    { context: this.context }
                );

                // remove the element so we do not need to refresh the page
                this.el.remove();
            },
        });
    },

    /**
      * Duplicate the room.
      *
      * @private
      */
    _onDuplicateClick: function (event) {
        event.preventDefault();
        event.stopPropagation();
        this.call("dialog", "add", ConfirmationDialog, {
            body: _t("Are you sure you want to duplicate this room?"),
            confirm: async () => {
                await this.orm.call("event.meeting.room", "copy", [this.meetingRoomId], {
                    context: this.context,
                });

                window.location.reload();
            },
        });
    },

    /**
      * Pin/unpin the room.
      *
      * @private
      */
    _onPinClick: async function (event) {
        event.preventDefault();
        event.stopPropagation();

        const pinnedButtonClass = "o_wevent_meeting_room_pinned";
        const isPinned = event.currentTarget.classList.contains(pinnedButtonClass);

        await this.orm.write(
            "event.meeting.room",
            [this.meetingRoomId],
            { is_pinned: !isPinned },
            { context: this.context }
        );

        // TDE FIXME: addclass ?
        if (isPinned) {
            event.currentTarget.classList.remove(pinnedButtonClass);
        } else {
            event.currentTarget.classList.add(pinnedButtonClass);
        }
    }
});

export default publicWidget.registry.websiteEventMeetingRoom;
