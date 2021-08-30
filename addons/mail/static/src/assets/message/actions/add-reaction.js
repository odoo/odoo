/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Adds the given reaction on this message.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Message/addReaction
        [Action/params]
            content
                [type]
                    String
            record
                [type]
                    Message
        [Action/behavior]
            :messageData
                @env
                .{Env/owlEnv}
                .{Dict/get}
                    services
                .{Dict/get}
                    rpc
                .{Function/call}
                    [route]
                        /mail/message/add_reaction
                    [params]
                        [content]
                            @content
                        [message_id]
                            @record
                            .{Message/id}
            {if}
                {Record/exists}
                    @record
                .{isFalsy}
            .{then}
                {break}
            {Record/update}
                [0]
                    @record
                [1]
                    @messageData
`;
