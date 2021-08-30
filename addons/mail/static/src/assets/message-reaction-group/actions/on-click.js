/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on the reaction group.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageReactionGroup/onClick
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    MessageReactionGroup
        [Action/behavior]
            {Event/markAsHandled}
                [0]
                    @ev
                [1]
                    MessageReactionGroup/onClick
            {if}
                @record
                .{MessageReactionGroup/hasUserReacted}
            .{then}
                {Message/removeReaction}
                    [0]
                        @record
                        .{MessageReactionGroup/message}
                    [1]
                        @record
                        .{MessageReactionGroup/content}
            .{else}
                {Message/addReaction}
                    [0]
                        @record
                        .{MessageReactionGroup/message}
                    [1]
                        @record
                        .{MessageReactionGroup/content}
`;
