/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            creditConditional
        [Element/model]
            SnailmailErrorComponent
        [Element/tag]
            t
        [Element/isPresent]
            @record
            .{SnailmailErrorError/snailmailErrorView}
            .{SnailmailErrorComponent/notification}
            .{Notification/failureType}
            .{=}
                sn_credit
`;
