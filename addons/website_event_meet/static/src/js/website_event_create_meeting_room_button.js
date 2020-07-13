odoo.define('website_event_meet.website_event_create_room_button', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
const core = require('web.core');
const QWeb = core.qweb;

publicWidget.registry.websiteEventCreateMeetingRoom = publicWidget.Widget.extend({
    selector: '.o_wevent_create_room_button',
    xmlDependencies: ['/website_event_meet/static/src/xml/website_event_meeting_room.xml'],
    events: {
        'click': '_onClick',
    },

    start: async function () {
        const langs = await this._rpc({
            route: "/event/active_langs",
        });

        this.$createModal = $(QWeb.render(
            'create_meeting_room_modal',
            {
                csrf_token: odoo.csrf_token,
                event: this.$el.data("event"),
                langs: langs,
            }
        ));

        // set the default language to the user language
        this.$createModal.find('.o_wevent_create_meeting_room_lang').val(this.$el.data("default-lang"));
        this.$createModal.appendTo(this.$el);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClick: async function () {
        this.$createModal.modal('show');
    },
});

return publicWidget.registry.websiteEventMeetingRoom;

});
