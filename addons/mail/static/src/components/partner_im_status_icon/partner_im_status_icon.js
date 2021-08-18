/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class PartnerImStatusIcon extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.partner}
     */
    get partner() {
        return this.messaging && this.messaging.models['mail.partner'].get(this.props.partnerLocalId);
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
        hasBackground: Boolean,
        /**
         * Determines whether a click on `this` should open a chat with
         * `this.partner`.
         */
        hasOpenChat: Boolean,
    },
    template: 'mail.PartnerImStatusIcon',
});

registerMessagingComponent(PartnerImStatusIcon);
