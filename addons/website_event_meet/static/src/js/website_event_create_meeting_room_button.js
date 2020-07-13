odoo.define('website_event_meet.website_event_create_room_button', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
const core = require('web.core');
const QWeb = core.qweb;

publicWidget.registry.websiteEventCreateMeetingRoom = publicWidget.Widget.extend({
    selector: '.o_wevent_create_room_button',
    xmlDependencies: ['/website_event_meet/static/src/xml/website_event_meeting_room.xml'],
    events: {
        'click': '_onClickCreate',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickCreate: async function () {
        if (!this.$createModal) {
            const langs = await this._rpc({
                route: "/event/active_langs",
            });

            this.$createModal = $(QWeb.render(
                'event_meet_create_room_modal',
                {
                    csrf_token: odoo.csrf_token,
                    eventId: this.$el.data("eventId"),
                    defaultLangCode: this.$el.data("defaultLangCode"),
                    langs: langs,
                }
            ));

            this.$createModal.appendTo(this.$el.parentNode);
        }

        this.$createModal.modal('show');
    },

    //--------------------------------------------------------------------------
    // Override
    //--------------------------------------------------------------------------

    /**
     * Remove the create modal from the DOM, to avoid issue when editing the template
     * with the website editor.
     *
     * @override
     */
    destroy: function () {
        $('.o_wevent_create_meeting_room_modal').remove();
        this._super.apply(this, arguments);
    },
});

return publicWidget.registry.websiteEventMeetingRoom;

});
