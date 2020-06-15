odoo.define('mail/static/src/components/partner_mention_suggestion/partner_mention_suggestion.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const components = {
    PartnerImStatusIcon: require('mail/static/src/components/partner_im_status_icon/partner_im_status_icon.js'),
};

const { Component } = owl;

class PartnerMentionSuggestion extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const partner = this.env.models['mail.partner'].get(props.partnerLocalId);
            return {
               partner: partner ? partner.__state : undefined,
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
     * @param {Event} ev
     */
    _onClick(ev) {
        // avoid following dummy href
        ev.preventDefault();
        this.trigger('o-partner-mention-suggestion-clicked', {
            partner: this.partner,
        });
    }

    /**
     * @private
     * @param {Event} ev
     */
    _onMouseOver(ev) {
        this.trigger('o-partner-mention-suggestion-mouse-over', {
            partner: this.partner,
        });
    }
}

Object.assign(PartnerMentionSuggestion, {
    components,
    defaultProps: {
        isActive: false,
    },
    props: {
        isActive: Boolean,
        partnerLocalId: String,
    },
    template: 'mail.PartnerMentionSuggestion',
});

return PartnerMentionSuggestion;

});
