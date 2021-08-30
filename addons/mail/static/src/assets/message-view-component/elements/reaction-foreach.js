/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            reaction
        [Element/model]
            MessageViewComponent
        [Record/models]
            Foreach
        [Field/target]
            MessageViewComponent:reaction
        [Foreach/collection]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/message}
            .{Message/messageReactionGroups}
        [Foreach/as]
            messageReactionGroup
        [Element/key]
            @field
            .{Foreach/get}
                messageReactionGroup
            .{Record/id}
        [MessageViewComponent:reaction/messageReactionGroup]
            @field
            .{Foreach/get}
                messageReactionGroup
`;
