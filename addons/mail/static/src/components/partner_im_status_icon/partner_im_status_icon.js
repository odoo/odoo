odoo.define('mail/static/src/components/partner_im_status_icon/partner_im_status_icon.js', function (require) {
'use strict';

const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');
const { markEventHandled } = require('mail/static/src/utils/utils.js');

const { Component } = owl;

class PartnerImStatusIcon extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
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
        markEventHandled(ev, 'PartnerImStatusIcon.openChat');
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
