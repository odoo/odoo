/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';

const { Component } = owl;

class PartnerImStatusIcon extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const partner = this.env.models['mail.partner'].get(props.partnerLocalId);
            return {
                partner,
                partnerImStatus: partner && partner.im_status,
                partnerRoot: this.env.messaging.partnerRoot,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.partner}
     */
    get partner() {
        return this.env.models['mail.partner'].get(this.props.partnerLocalId);
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

export default PartnerImStatusIcon;
