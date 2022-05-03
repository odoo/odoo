/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ComposerSuggestionList extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ComposerSuggestionListView}
     */
    get composerSuggestionListView() {
        return this.messaging && this.messaging.models['ComposerSuggestionListView'].get(this.props.localId);
    }

}

Object.assign(ComposerSuggestionList, {
    props: { localId: String },
    template: 'mail.ComposerSuggestionList',
});

registerMessagingComponent(ComposerSuggestionList);
