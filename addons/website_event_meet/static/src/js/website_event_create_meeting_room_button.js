/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { renderToElement } from "@web/core/utils/render";

publicWidget.registry.websiteEventCreateMeetingRoom = publicWidget.Widget.extend({
    selector: '.o_wevent_create_room_button',
    events: {
        'click': '_onClickCreate',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickCreate: async function () {
        if (!this.createModalEl) {
            const langs = await rpc("/event/active_langs");

            this.createModalEl = renderToElement("event_meet_create_room_modal", {
                csrf_token: odoo.csrf_token,
                eventId: this.el.dataset.eventId,
                defaultLangCode: this.el.dataset.defaultLangCode,
                langs: langs,
            });
            this.el.parentNode.append(this.createModalEl);
        }

        Modal.getOrCreateInstance(this.createModalEl).show();
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
        const modalEl = document.querySelector(".o_wevent_create_meeting_room_modal");
        if (modalEl) {
            modalEl.remove();
        }
        this._super.apply(this, arguments);
    },
});

export default publicWidget.registry.websiteEventMeetingRoom;
