/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AutocompleteInputSuggestionListView extends Component {

    /**
     * @override
     */
     setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
    }

    /**
     * @returns {AutocompleteInputSuggestionListView}
     */
    get autocompleteInputSuggestionListView() {
        return this.props.record;
    }

}

Object.assign(AutocompleteInputSuggestionListView, {
    props: { record: Object },
    template: 'mail.AutocompleteInputSuggestionListView',
});

registerMessagingComponent(AutocompleteInputSuggestionListView);
