/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted } = owl;

export class AutocompleteInputView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        onMounted(() => this._mounted());
    }

    _mounted() {
        if (!this.root.el) {
            return;
        }
        if (this.autocompleteInputView.isFocusOnMount) {
            this.root.el.focus();
        }
    }

    /**
     * @returns {AutocompleteInputView}
     */
    get autocompleteInputView() {
        return this.props.record;
    }

}

Object.assign(AutocompleteInputView, {
    props: { record: Object },
    template: 'mail.AutocompleteInputView',
});

registerMessagingComponent(AutocompleteInputView);
