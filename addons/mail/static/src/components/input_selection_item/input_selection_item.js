/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class InputSelectionItem extends Component {

    /**
     * @returns {InputSelectionItem}
     */
    get inputSelectionItem() {
        return this.props.record;
    }

}

Object.assign(InputSelectionItem, {
    props: { record: Object },
    template: 'mail.InputSelectionItem',
});

registerMessagingComponent(InputSelectionItem);
