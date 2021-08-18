/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ComposerSuggestionList extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.composer}
     */
    get composer() {
        return this.messaging && this.messaging.models['mail.composer'].get(this.props.composerLocalId);
    }

}

Object.assign(ComposerSuggestionList, {
    defaultProps: {
        isBelow: false,
    },
    props: {
        composerLocalId: String,
        isBelow: Boolean,
    },
    template: 'mail.ComposerSuggestionList',
});

registerMessagingComponent(ComposerSuggestionList);
