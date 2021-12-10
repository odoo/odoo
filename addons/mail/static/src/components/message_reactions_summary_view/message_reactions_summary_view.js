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
        useComponentToModel({ fieldName: 'component', modelName: 'MessageReactionsSummaryView', propNameAsRecordLocalId: 'localId' });
    }

    get messageReactionsSummaryView() {
        return this.messaging && this.messaging.models['MessageReactionsSummaryView'].get(this.props.localId);
    }

}

Object.assign(MessageReactionsSummaryView, {
    props: {
        localId: String,
    },
    template: 'mail.MessageReactionsSummaryView',
});

registerMessagingComponent(MessageReactionsSummaryView);
