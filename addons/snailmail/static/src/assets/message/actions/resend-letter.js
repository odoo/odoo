/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Retries to send the 'snailmail.letter' corresponding to this message.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Message/resendLetter
        [Action/feature]
            snailmail
        [Action/params]
            message
                [type]
                    Message
        [Action/behavior]
            {Dev/comment}
                the result will come from longpolling: message_notification_update
            {Record/doAsync}
                [0]
                    @message
                [1]
                    @env
                    .{Env/owlEnv}
                    .{Dict/get}
                        services
                    .{Dict/get}
                        rpc
                    .{Function/call}
                        [model]
                            mail.message
                        [method]
                            send_letter
                        [args]
                            {Record/insert}
                                [Record/models]
                                    Collection
                                {Record/insert}
                                    [Record/models]
                                        Collection
                                    @message
                                    .{Message/id}
`;
