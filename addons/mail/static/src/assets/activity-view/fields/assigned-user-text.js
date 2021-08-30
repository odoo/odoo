/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Compute the string for the assigned user.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            assignedUserText
        [Field/model]
            ActivityView
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{ActivityView/activity}
                .{Activity/assignee}
                .{isFalsy}
            .{then}
                {Record/empty}
            .{else}
                {String/sprintf}
                    [0]
                        {Locale/text}
                            for %s
                    [1]
                        @record
                        .{ActivityView/activity}
                        .{Activity/assignee}
                        .{User/nameOrDisplayName}
`;
