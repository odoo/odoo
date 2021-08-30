/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Format the summary.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            summary
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
                .{Activity/summary}
                .{isFalsy}
            .{then}
                {Record/empty}
            .{else}
                {String/sprintf}
                    [0]
                        {Locale/text}
                            “%s”
                    [1]
                        @record
                        .{ActivityView/activity}
                        .{Activity/summary}
`;
