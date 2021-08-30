/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            trialConditional
        [Element/model]
            SnailmailErrorComponent
        [web.Element/tag]
            t
        [Element/isPresent]
            @record
            .{SnailmailErrorComponent/snailmailErrorView}
            .{SnailmailErrorView/notification}
            .{Notification/failureType}
            .{=}
                sn_trial
`;
