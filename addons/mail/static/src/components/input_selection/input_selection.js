/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class InputSelection extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
    }

    /**
     * @returns {InputSelection}
     */
    get inputSelection() {
        return this.props.record;
    }

}

Object.assign(InputSelection, {
    props: { record: Object },
    template: 'mail.InputSelection',
});

registerMessagingComponent(InputSelection);
