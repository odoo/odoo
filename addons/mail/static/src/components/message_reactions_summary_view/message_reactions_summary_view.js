/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { replace } from '@mail/model/model_field_command';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';

const { Component } = owl;

export class MessageReactionsSummaryView extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'mail.message_reactions_summary_view', propNameAsRecordLocalId: 'messageReactionsSummaryViewLocalId' });
    }

    get messageReactionsSummaryView() {
        return this.messaging && this.messaging.models['mail.message_reactions_summary_view'].get(this.props.messageReactionsSummaryViewLocalId);
    }

}

Object.assign(MessageReactionsSummaryView, {
    props: {
        messageReactionsSummaryViewLocalId: String,
    },
    template: 'mail.MessageReactionsSummaryView',
});

registerMessagingComponent(MessageReactionsSummaryView);
