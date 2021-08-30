/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/action]
            Message/openResendAction
        [ActionAddon/feature]
            sms
        [ActionAddon/params]
            message
        [ActionAddon/behavior]
            {if}
                @message
                .{Message/type}
                .{=}
                    sms
            .{then}
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
                            sms.sms_resend_action
                        [options]
                            [additional_context]
                                [default_mail_message_id]
                                    @message
                                    .{Message/id}
            .{else}
                @original
`;
