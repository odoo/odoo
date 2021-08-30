/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens the view that allows to resend the message in case of failure.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Message/openResendAction
        [Action/params]
            message
                [type]
                    Message
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                bus
            .{Dict/get}
                trigger
            .{Function/call}
                [0]
                    do-action
                [1]
                    [action]
                        mail.mail_resend_message_action
                    [options]
                        [additional_context]
                            [mail_message_to_resend]
                                @message
                                .{Message/id}
`;
