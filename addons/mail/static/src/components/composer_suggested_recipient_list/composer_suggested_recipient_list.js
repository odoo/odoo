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

    /**
     * @returns {Thread}
     */
    get thread() {
        return this.messaging && this.messaging.models['Thread'].get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickShowLess(ev) {
        if (!this.composerSuggestedRecipientListView) {
            return;
        }
        this.composerSuggestedRecipientListView.update({ hasShowMoreButton: false });
    }

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
    props: {
        localId: String,
        threadLocalId: String,
    },
    template: 'mail.ComposerSuggestedRecipientList',
});

registerMessagingComponent(ComposerSuggestedRecipientList);
