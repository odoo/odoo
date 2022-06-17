/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class InputSelectionPrompt extends Component {

    /**
     * @returns {InputSelectionPromptView}
     */
    get inputSelectionPromptView() {
        return this.props.record;
    }

}

Object.assign(InputSelectionPrompt, {
    props: { record: Object },
    template: 'mail.InputSelectionPrompt',
});

registerMessagingComponent(InputSelectionPrompt);
