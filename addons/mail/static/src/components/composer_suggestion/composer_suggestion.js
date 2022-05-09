/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update';
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
        return this.props.record;
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
            this.composerSuggestion &&
            this.composerSuggestion.composerViewOwner &&
            this.composerSuggestion.composerViewOwner.hasToScrollToActiveSuggestion &&
            this.composerSuggestion.isActive
        ) {
            this.root.el.scrollIntoView({
                block: 'center',
            });
            this.composerSuggestion.composerViewOwner.update({ hasToScrollToActiveSuggestion: false });
        }
    }

}

Object.assign(ComposerSuggestion, {
    props: { record: Object },
    template: 'mail.ComposerSuggestion',
});

registerMessagingComponent(ComposerSuggestion);
