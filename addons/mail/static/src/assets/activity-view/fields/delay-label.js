/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Compute the label for "when" the activity is due.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            delayLabel
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
                .{Activity/dateDeadline}
                .{isFalsy}
            .{then}
                {Record/empty}
                {break}
            :today
                {Record/insert}
                    [Record/models]
                        Moment
                    {Time/currentDateEveryMinute}
                    .{Date/getTime}
                    .{DateTime/startOf}
                        day
            :momentDeadlineDate
                {Record/insert}
                    [Record/models]
                        Moment
                    {String/autoToDate}
                        @record
                        .{ActivityView/activity}
                        .{Activity/dateDeadline}
            {Dev/comment}
                true means no rounding
            :diff
                {Moment/diff}
                    [0]
                        @momentDeadlineDate
                    [1]
                        @today
                    [2]
                        days
                    [3]
                        true
            {if}
                @diff
                .{=}
                    0
            .{then}
                {Locale/text}
                    Today:
            .{elif}
                @diff
                .{=}
                    -1
            .{then}
                {Locale/text}
                    Yesterday:
            .{elif}
                @diff
                .{<}
                    0
            .{then}
                {String/sprintf}
                    [0]
                        {Locale/text}
                            %d days overdue:
                    [1]
                        {Math/abs}
                            @diff
            .{elif}
                @diff
                .{=}
                    1
            .{then}
                {Locale/text}
                    Tomorrow:
            .{else}
                {String/sprintf}
                    [0]
                        {Locale/text}
                            Due in %d days:
                    [1]
                        {Math/abs}
                            @diff
`;
