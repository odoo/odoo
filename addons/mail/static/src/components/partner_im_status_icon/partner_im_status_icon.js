odoo.define('mail/static/src/components/partner_im_status_icon/partner_im_status_icon.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class PartnerImStatusIcon extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const partner = this.env.models['mail.partner'].get(props.partnerLocalId);
            return {
                partner: partner ? partner.__state : undefined,
                partnerRoot: this.env.messaging.partnerRoot
                    ? this.env.messaging.partnerRoot.__state
                    : undefined,
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

return PartnerImStatusIcon;

});
