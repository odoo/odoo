/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AutocompleteInputSuggestionItemView extends Component {
    get autocompleteInputSuggestionItemView() {
        return this.messaging && this.messaging.models['AutocompleteInputSuggestionItemView'].get(this.props.localId);
    }
}

Object.assign(AutocompleteInputSuggestionItemView, {
    props: { localId: String },
    template: 'mail.AutocompleteInputSuggestionItemView',
});

registerMessagingComponent(AutocompleteInputSuggestionItemView);
