/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MessageReactionGroup
        [Model/fields]
            content
            count
            guests
            hasUserReacted
            message
            messageId
            partners
            summary
        [Model/id]
            MessageReactionGroup/message
            .{&}
                MessageReactionGroup/content
        [Model/actions]
            MessageReactionGroup/onClick
`;
