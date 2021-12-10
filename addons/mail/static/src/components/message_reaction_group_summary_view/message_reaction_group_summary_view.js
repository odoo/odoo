/** @odoo-module **/

const { Component } = owl;
import { registerMessagingComponent } from '@mail/utils/messaging_component';

export class MessageReactionGroupSummaryView extends Component {

    get messageReactionGroupSummaryView() {
        return this.messaging.models['MessageReactionGroupSummaryView'].get(this.props.localId);
    }

}

Object.assign(MessageReactionGroupSummaryView, {
    props: {
        localId: String,
    },
    template: 'mail.MessageReactionGroupSummaryView',
});

registerMessagingComponent(MessageReactionGroupSummaryView);
