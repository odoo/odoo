/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update';
import { replace } from '@mail/model/model_field_command';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ComposerSuggestion extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useUpdate({ func: () => this._update() });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ComposerSuggestion}
     */
    get composerSuggestion() {
        return this.messaging && this.messaging.models['ComposerSuggestion'].get(this.props.localId);
    }

    /**
     * @returns {ComposerView}
     */
    get composerView() {
        return this.messaging && this.messaging.models['ComposerView'].get(this.props.composerViewLocalId);
    }

    /**
     * Returns a descriptive title for this suggestion. Useful to be able to
     * read both parts when they are overflowing the UI.
     *
     * @returns {string}
     */
    title() {
        if (this.composerSuggestion.cannedResponse) {
            return _.str.sprintf("%s: %s", this.composerSuggestion.record.source, this.composerSuggestion.record.substitution);
        }
        if (this.composerSuggestion.thread) {
            return this.composerSuggestion.record.name;
        }
        if (this.composerSuggestion.channelCommand) {
            return _.str.sprintf("%s: %s", this.composerSuggestion.record.name, this.composerSuggestion.record.help);
        }
        if (this.composerSuggestion.partner) {
            if (this.composerSuggestion.record.email) {
                return _.str.sprintf("%s (%s)", this.composerSuggestion.record.nameOrDisplayName, this.composerSuggestion.record.email);
            }
            return this.composerSuggestion.record.nameOrDisplayName;
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
            this.root.el &&
            this.composerView &&
            this.composerView.hasToScrollToActiveSuggestion &&
            this.props.isActive
        ) {
            this.root.el.scrollIntoView({
                block: 'center',
            });
            this.composerView.update({ hasToScrollToActiveSuggestion: false });
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
        this.composerView.update({ activeSuggestion: replace(this.composerSuggestion) });
        this.composerView.insertSuggestion();
        this.composerView.closeSuggestions();
        this.composerView.update({ doFocus: true });
    }

}

Object.assign(ComposerSuggestion, {
    defaultProps: {
        isActive: false,
    },
    props: {
        composerViewLocalId: String,
        isActive: { type: Boolean, optional: true },
        localId: String,
    },
    template: 'mail.ComposerSuggestion',
});

registerMessagingComponent(ComposerSuggestion);
