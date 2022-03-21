/** @odoo-module */

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageActionList extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'actionReactionRef', modelName: 'MessageActionList', refName: 'actionReaction' });
        this.ADD_A_REACTION = this.env._t("Add a Reaction");
    }

    /**
     * @returns {MessageActionList}
     */
    get messageActionList() {
        return this.messaging && this.messaging.models['MessageActionList'].get(this.props.localId);
    }

}

Object.assign(MessageActionList, {
    props: { localId: String },
    template: "mail.MessageActionList",
});

registerMessagingComponent(MessageActionList);
