/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            SnailmailErrorView/onClickCancelLetter
        [Action/params]
            record
                [type]
                    SnailmailErrorView
        [Action/behavior]
            {Message/cancelLetter}
                @record
                .{SnailmailErrorView/message}
            {Record/delete}
                @record
                .{SnailmailErrorView/dialogOwner}
`;
