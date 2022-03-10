/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AutocompleteInputView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'AutocompleteInputView' });
        useRefToModel({ fieldName: 'inputRef', modelName: 'AutocompleteInputView', refName: 'root' });
        useUpdateToModel({ methodName: 'onComponentUpdate', modelName: 'AutocompleteInputView' });
    }

    get autocompleteInputView() {
        return this.messaging && this.messaging.models['AutocompleteInputView'].get(this.props.localId);
    }

}

Object.assign(AutocompleteInputView, {
    props: { localId: String },
    template: 'mail.AutocompleteInputView',
});

registerMessagingComponent(AutocompleteInputView);
