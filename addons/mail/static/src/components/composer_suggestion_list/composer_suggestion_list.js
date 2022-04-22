/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ComposerSuggestionList extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ComposerView}
     */
    get composerView() {
        return this.messaging && this.messaging.models['ComposerView'].get(this.props.composerViewLocalId);
    }

}

Object.assign(ComposerSuggestionList, {
    props: {
        composerViewLocalId: String,
    },
    template: 'mail.ComposerSuggestionList',
});

registerMessagingComponent(ComposerSuggestionList);
