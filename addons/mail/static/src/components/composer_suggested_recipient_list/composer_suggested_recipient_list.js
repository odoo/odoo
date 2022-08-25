/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ComposerSuggestedRecipientList extends Component {

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

Object.assign(ComposerSuggestedRecipientList, {
    props: { record: Object },
    template: 'mail.ComposerSuggestedRecipientList',
});

registerMessagingComponent(ComposerSuggestedRecipientList);
