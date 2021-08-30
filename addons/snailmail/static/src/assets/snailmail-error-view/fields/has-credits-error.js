/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasCreditsError
        [Field/model]
            SnailmailErrorView
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{SnailmailErrorView/notification}
            .{&}
                @record
                .{SnailmailErrorView/notification}
                .{Notification/failureType}
                .{=}
                    sn_credit
                .{|}
                    @record
                    .{SnailmailErrorView/notification}
                    .{Notification/failureType}
                    .{=}
                        sn_trial
`;
