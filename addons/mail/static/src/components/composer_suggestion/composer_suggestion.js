odoo.define('mail/static/src/components/composer_suggestion/composer_suggestion.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const components = {
    PartnerImStatusIcon: require('mail/static/src/components/partner_im_status_icon/partner_im_status_icon.js'),
};

const { Component } = owl;

class ComposerSuggestion extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const record = this.env.models[props.modelName].get(props.recordLocalId);
            return {
               record: record ? record.__state : undefined,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.composer}
     */
    get composer() {
        return this.env.models['mail.composer'].get(this.props.composerLocalId);
    }

    get isCannedResponse() {
        return this.props.modelName === "mail.canned_response";
    }

    get isChannel() {
        return this.props.modelName === "mail.thread";
    }

    get isCommand() {
        return this.props.modelName === "mail.channel_command";
    }

    get isPartner() {
        return this.props.modelName === "mail.partner";
    }

    get record() {
        return this.env.models[this.props.modelName].get(this.props.recordLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClick(ev) {
        ev.preventDefault();
        this.composer.insertSuggestion(this.record);
        this.composer.closeSuggestions();
        this.trigger('o-composer-suggestion-clicked');
    }

    /**
     * @private
     * @param {Event} ev
     */
    _onMouseOver(ev) {
        this.composer.update({
            [this.composer.activeSuggestedRecordName]: [['link', this.record]],
        });
    }

}

Object.assign(ComposerSuggestion, {
    components,
    defaultProps: {
        isActive: false,
    },
    props: {
        composerLocalId: String,
        isActive: Boolean,
        modelName: String,
        recordLocalId: String,
    },
    template: 'mail.ComposerSuggestion',
});

return ComposerSuggestion;

});
