/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Updates the message's content.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Message/updateContent
        [Action/params]
            attachment_ids
                [type]
                    Collection<Integer>
            body
                [type]
                    String
                [description]
                    the new body of the message
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
                        /mail/message/update_content
                    [params]
                        [attachment_ids]
                            @attachment_ids
                        [body]
                            @body
                        [message_id]
                            @record
                            .{Message/id}
            {if}
                {Record/exists}
                    @record
                .{isFalsy}
            .{then}
                {break}
            {Record/insert}
                [Record/models]
                    Message
                @messageData
`;
