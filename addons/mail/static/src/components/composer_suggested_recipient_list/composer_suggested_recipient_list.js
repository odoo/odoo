/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
