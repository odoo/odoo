/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class PartnerImStatusIcon extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Partner}
     */
    get partner() {
        return this.messaging && this.messaging.models['Partner'].get(this.props.partnerLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        if (!this.props.hasOpenChat) {
            return;
        }
        this.partner.openChat();
    }

}

Object.assign(PartnerImStatusIcon, {
    defaultProps: {
        hasBackground: true,
        hasOpenChat: false,
    },
    props: {
        partnerLocalId: String,
        hasBackground: { type: Boolean, optional: true },
        /**
         * Determines whether a click on `this` should open a chat with
         * `this.partner`.
         */
        hasOpenChat: { type: Boolean, optional: true },
    },
    template: 'mail.PartnerImStatusIcon',
});

registerMessagingComponent(PartnerImStatusIcon);
