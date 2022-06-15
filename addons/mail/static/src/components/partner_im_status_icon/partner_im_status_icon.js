/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { markEventHandled } from '@mail/utils/utils';

const { Component } = owl;

export class PartnerImStatusIcon extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {PartnerImStatusIconView}
     */
    get partnerImStatusIconView() {
        return this.props.record;
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
        if (!this.props.hasOpenChat || !this.partnerImStatusIconView.persona.partner) {
            return;
        }
        this.partnerImStatusIconView.persona.partner.openChat();
    }

}

Object.assign(PartnerImStatusIcon, {
    defaultProps: {
        hasBackground: true,
        hasOpenChat: false,
    },
    props: {
        hasBackground: { type: Boolean, optional: true },
        /**
         * Determines whether a click on `this` should open a chat with
         * `this.partner`.
         */
        hasOpenChat: { type: Boolean, optional: true },
        record: Object,
    },
    template: 'mail.PartnerImStatusIcon',
});

registerMessagingComponent(PartnerImStatusIcon);
