/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AutocompleteInputSuggestionView extends Component {

    /**
     * @returns {AutocompleteInputSuggestionView}
     */
    get autocompleteInputSuggestionView() {
        return this.props.record;
    }

}

Object.assign(AutocompleteInputSuggestionView, {
    props: { record: Object },
    template: 'mail.AutocompleteInputSuggestionView',
});

registerMessagingComponent(AutocompleteInputSuggestionView);
