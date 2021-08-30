/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            SnailmailErrorView/onClickResendLetter
        [Action/params]
            record
                [type]
                    SnailmailErrorView
        [Action/behavior]
            {Message/resendLetter}
                @record
                .{SnailmailErrorView/message}
            {Record/delete}
                @record
                .{SnailmailErrorView/dialogOwner}
`;
