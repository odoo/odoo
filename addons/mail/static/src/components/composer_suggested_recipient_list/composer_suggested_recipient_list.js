/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ComposerSuggestedRecipientListView extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ComposerSuggestedRecipientListView}
     */
    get composerSuggestedRecipientListView() {
        return this.props.record;
    }

}

Object.assign(ComposerSuggestedRecipientListView, {
    props: { record: Object },
    template: 'mail.ComposerSuggestedRecipientListView',
});

registerMessagingComponent(ComposerSuggestedRecipientListView);
