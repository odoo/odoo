/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens the action about 'snailmail.letter' format error.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Message/openFormatLetterAction
        [Action/feature]
            snailmail
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
                        snailmail.snailmail_letter_format_error_action
                    [options]
                        [additional_context]
                            [message_id]
                                @message
                                .{Message/id}
`;
