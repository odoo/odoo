odoo.define('website_event_meet.website_event_meet_meeting_room', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
const core = require('web.core');
const Dialog = require('web.Dialog');
const _t = core._t;

publicWidget.registry.websiteEventMeetingRoom = publicWidget.Widget.extend({
    selector: '.o_wevent_meeting_room_card',
    xmlDependencies: ['/website_event_meet/static/src/xml/website_event_meeting_room.xml'],
    events: {
        'click .o_wevent_meeting_room_delete': '_onDeleteClick',
        'click .o_wevent_meeting_room_duplicate': '_onDuplicateClick',
    },

    start: function () {
        this._super.apply(this, arguments);
        this.meetingRoomId = parseInt(this.$el.data('meeting-room-id'));
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

        Dialog.confirm(
            this,
            _t("Are you sure you want to close this room ?"),
            {
                confirm_callback: async () => {
                    await this._rpc({
                        model: 'event.meeting.room',
                        method: 'write',
                        args: [this.meetingRoomId, {active: false}],
                        context: this.context,
                    });

                    // remove the element so we do not need to refresh the page
                    this.$el.remove();
                }
            },
        );
    },

    /**
      * Duplicate the room.
      *
      * @private
      */
    _onDuplicateClick: function (event) {
        event.preventDefault();
        event.stopPropagation();
        Dialog.confirm(
            this,
            _t("Are you sure you want to duplicate this room ?"),
            {
                confirm_callback: async () => {
                    await this._rpc({
                        model: 'event.meeting.room',
                        method: 'copy',
                        args: [this.meetingRoomId],
                        context: this.context,
                    });

                    window.location.reload();
                }
            },
        );
    },
});

return publicWidget.registry.websiteEventMeetingRoom;

});
