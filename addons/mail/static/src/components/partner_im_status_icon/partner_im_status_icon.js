/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { markEventHandled } from '@mail/utils/utils';

const { Component } = owl;

export class PartnerImStatusIcon extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Partner}
     */
    get partner() {
        return this.props.partner;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        markEventHandled(ev, 'PartnerImStatusIcon.Click');
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
        partner: Object,
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
