/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the classname of the icon for this notification.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            iconClass
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
                    fa
                    fa-check
                [bounce]
                    fa
                    fa-exclamation
                [exception]
                    fa
                    fa-exclamation
                [ready]
                    fa
                    fa-send-o
                [canceled]
                    fa
                    fa-trash-o
`;
