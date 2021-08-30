/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the date of this message as a string (either a relative period
        in the near past or an actual date for older dates).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            dateDay
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{Message/date}
                .{isFalsy}
            .{then}
                {Dev/comment}
                    Without a date, we assume that it's a today message. This is
                    mainly done to avoid flicker inside the UI.
                {Locale/text}
                    Today
                {break}
            :date
                @record
                .{Message/date}
                .{Moment/format}
                    YYYY-MM-DD
            {if}
                @dat
                .{=}
                    {Record/insert}
                        [Record/models]
                            Moment
                    .{Moment/YYYY-MM-DD}
            .{then}
                {Locale/text}
                    Today
            .{elif}
                @date
                .{=}
                    {Record/insert}
                        [Record/models]
                            Moment
                    .{Moment/subtract}
                        [0]
                            1
                        [1]
                            days
                    .{Moment/format}
                        YYYY-MM-DD
            .{then}
                {Locale/text}
                    Yesterday
            .{else}
                @record
                .{Message/date}
                .{Moment/format}
                    LL
`;
