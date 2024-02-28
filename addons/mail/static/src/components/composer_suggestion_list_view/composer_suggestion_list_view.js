/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ComposerSuggestionListView extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ComposerSuggestionListView}
     */
    get composerSuggestionListView() {
        return this.props.record;
    }

}

Object.assign(ComposerSuggestionListView, {
    props: { record: Object },
    template: 'mail.ComposerSuggestionListView',
});

registerMessagingComponent(ComposerSuggestionListView);
