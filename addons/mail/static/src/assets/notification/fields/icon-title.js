/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the text to display as title for this notification.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            iconTitle
        [Field/model]
            Notification
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {switch}
                @record
                .{Notification/status}
            .{case}
                [sent]
                    {Locale/text}
                        Sent
                [bounce]
                    {Locale/text}
                        Bounced
                [exception]
                    {Locale/text}
                        Error
                [ready]
                    {Locale/text}
                        Ready
                [canceled]
                    {Locale/text}
                        Canceled
`;
