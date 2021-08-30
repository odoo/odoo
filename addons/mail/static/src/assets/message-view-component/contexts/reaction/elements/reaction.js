/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            reaction
        [Element/model]
            MessageViewComponent:reaction
        [Field/target]
            MessageReactionGroupComponent
        [MessageReactionGroupComponent/messageReactionGroup]
            @record
            .{MessageViewComponent:reaction/messageReactionGroup}
`;
