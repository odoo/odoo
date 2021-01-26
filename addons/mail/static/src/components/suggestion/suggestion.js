odoo.define('mail/static/src/components/suggestion/suggestion.js', function (require) {
'use strict';

const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');
const { link } = require('mail/static/src/model/model_field_command.js');

const components = {
    PartnerImStatusIcon: require('mail/static/src/components/partner_im_status_icon/partner_im_status_icon.js'),
};

const { Component } = owl;

class Suggestion extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const record = this.env.models[props.modelName].get(props.recordLocalId);
            const suggestionManager = this.env.models['mail.suggestionManager'].get(props.suggestionManagerLocalId);
            return {
                record: record ? record.__state : undefined,
                suggestionManager: suggestionManager ? suggestionManager.__state : undefined,
            };
        });
    }

    /**
     * @returns {mail.suggestion}
     */
    get suggestionManager() {
        return this.env.models['mail.suggestionManager'].get(this.props.suggestionManagerLocalId);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
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

    /**
     * Returns a descriptive title for this suggestion. Useful to be able to
     * read both parts when they are overflowing the UI.
     *
     * @returns {string}
     */
    title() {
        if (this.isCannedResponse) {
            return _.str.sprintf("%s: %s", this.record.source, this.record.substitution);
        }
        if (this.isChannel) {
            return this.record.name;
        }
        if (this.isCommand) {
            return _.str.sprintf("%s: %s", this.record.name, this.record.help);
        }
        if (this.isPartner) {
            if (this.record.email) {
                return _.str.sprintf("%s (%s)", this.record.nameOrDisplayName, this.record.email);
            }
            return this.record.nameOrDisplayName;
        }
        return "";
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _update() {
        if (
            this.suggestionManager.hasToScrollToActiveSuggestion &&
            this.props.isActive
        ) {
            this.el.scrollIntoView({
                block: 'center',
            });
            this.suggestionManager.update({ hasToScrollToActiveSuggestion: false });
        }
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
        this.suggestionManager.update({ activeSuggestedRecord: link(this.record) });
        this.trigger('suggestion-selected', true);
        this.suggestionManager.closeSuggestions();
        this.trigger('o-composer-suggestion-clicked');
    }

}

Object.assign(Suggestion, {
    components,
    props: {
        suggestionManagerLocalId: String,
        isActive: Boolean,
        modelName: String,
        recordLocalId: String,
    },
    template: 'mail.Suggestion',
});

return Suggestion;

});
