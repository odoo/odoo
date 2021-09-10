/** @odoo-module **/

const { Component } = owl;
import { registerMessagingComponent } from '@mail/utils/messaging_component';

export class MessageReactionGroupSummaryView extends Component {

    get messageReactionGroupSummaryView() {
        return this.messaging.models['mail.message_reaction_group_summary_view'].get(this.props.messageReactionGroupSummaryViewLocalId);
    }

}

Object.assign(MessageReactionGroupSummaryView, {
    props: {
        messageReactionGroupSummaryViewLocalId: String,
    },
    template: 'mail.MessageReactionGroupSummaryView',
});

registerMessagingComponent(MessageReactionGroupSummaryView);
