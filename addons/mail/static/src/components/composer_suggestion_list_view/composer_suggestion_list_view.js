/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
