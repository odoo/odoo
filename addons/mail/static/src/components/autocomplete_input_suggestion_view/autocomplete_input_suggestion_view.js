/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AutocompleteInputSuggestionView extends Component {
    get autocompleteInputSuggestionView() {
        return this.messaging && this.messaging.models['AutocompleteInputSuggestionView'].get(this.props.localId);
    }
}

Object.assign(AutocompleteInputSuggestionView, {
    props: { localId: String },
    template: 'mail.AutocompleteInputSuggestionView',
});

registerMessagingComponent(AutocompleteInputSuggestionView);
