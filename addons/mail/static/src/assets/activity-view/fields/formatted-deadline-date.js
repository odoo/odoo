/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Format the deadline date to something human reabable.Format the create date to something human readable.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            formattedDeadlineDate
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
            .{else}
                :momentDeadlineDate
                    {Record/insert}
                        [Record/models]
                            Moment
                    {String/autoToDate}
                        @record
                        .{ActivityView/activity}
                        .{Activity/dateDeadline}
                :datetimeFormat
                    {Locale/getLangDateFormat}
                @momentDeadlineDate
                .{Moment/format}
                    @datetimeFormat
`;
