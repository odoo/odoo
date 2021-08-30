/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            SnailmailErrorView/onClickClose
        [Action/params]
            record
                [type]
                    SnailmailErrorView
        [Action/behavior]
            {Record/delete}
                @record
                .{SnailmailErrorView/dialogOwner}
`;
