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

    get isCannedResponse() {
        return this.props.modelName === "CannedResponse";
    }

    get isChannel() {
        return this.props.modelName === "Thread";
    }

    get isPartner() {
        return this.props.modelName === "Partner";
    }

    get record() {
        return this.messaging && this.messaging.models[this.props.modelName].get(this.props.recordLocalId);
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
        if (this.composerSuggestion.channelCommand) {
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
        modelName: String,
        recordLocalId: String,
    },
    template: 'mail.ComposerSuggestion',
});

registerMessagingComponent(ComposerSuggestion);
