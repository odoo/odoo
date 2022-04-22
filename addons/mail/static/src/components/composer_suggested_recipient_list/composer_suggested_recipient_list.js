/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, useState } = owl;

export class ComposerSuggestedRecipientList extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this.state = useState({
            hasShowMoreButton: false,
        });
    }

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
        this.state.hasShowMoreButton = false;
    }

    /**
     * @private
     */
    _onClickShowMore(ev) {
        this.state.hasShowMoreButton = true;
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
