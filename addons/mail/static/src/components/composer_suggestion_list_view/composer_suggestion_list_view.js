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
        return this.props.record;
    }

}

Object.assign(ComposerSuggestionList, {
    props: { record: Object },
    template: 'mail.ComposerSuggestionList',
});

registerMessagingComponent(ComposerSuggestionList);
