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
        return this.messaging && this.messaging.models['ComposerSuggestedRecipientListView'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickShowMore(ev) {
        if (!this.composerSuggestedRecipientListView) {
            return;
        }
        this.composerSuggestedRecipientListView.update({ hasShowMoreButton: true });
    }

}

Object.assign(ComposerSuggestedRecipientList, {
    props: { localId: String },
    template: 'mail.ComposerSuggestedRecipientList',
});

registerMessagingComponent(ComposerSuggestedRecipientList);
