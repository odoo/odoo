odoo.define('mail/static/src/components/canned_response_suggestion/canned_response_suggestion.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class CannedResponseSuggestion extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const cannedResponse = this.env.models['mail.canned_response'].get(props.cannedResponseLocalId);
            return {
               cannedResponse: cannedResponse ? cannedResponse.__state : undefined,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.canned_response}
     */
    get cannedResponse() {
        return this.env.models['mail.canned_response'].get(this.props.cannedResponseLocalId);
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
        this.trigger('o-canned-response-suggestion-clicked', {
            cannedResponse: this.cannedResponse,
        });
    }

    /**
     * @private
     * @param {Event} ev
     */
    _onMouseOver(ev) {
        this.trigger('o-canned-response-suggestion-mouse-over', {
            cannedResponse: this.cannedResponse,
        });
    }
}

Object.assign(CannedResponseSuggestion, {
    defaultProps: {
        isActive: false,
    },
    props: {
        cannedResponseLocalId: String,
        isActive: Boolean,
    },
    template: 'mail.CannedResponseSuggestion',
});

return CannedResponseSuggestion;

});
