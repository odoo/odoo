/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { renderToElement } from "@web/core/utils/render";

publicWidget.registry.websiteEventCreateMeetingRoom = publicWidget.Widget.extend({
    selector: '.o_wevent_create_room_button',
    events: {
        'click': '_onClickCreate',
    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickCreate: async function () {
        if (!this.$createModal) {
            const langs = await this.rpc("/event/active_langs");

            this.$createModal = $(renderToElement(
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

export default publicWidget.registry.websiteEventMeetingRoom;
