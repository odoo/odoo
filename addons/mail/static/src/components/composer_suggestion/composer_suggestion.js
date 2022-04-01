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
    },
    template: 'mail.ComposerSuggestion',
});

registerMessagingComponent(ComposerSuggestion);
