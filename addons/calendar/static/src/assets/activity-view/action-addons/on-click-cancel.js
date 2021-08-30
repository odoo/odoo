/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/feature]
            calendar
        [ActionAddon/name]
            ActivityView/onClickCancel
        [Action/behavior]
            {if}
                @record
                .{ActivityView/activity}
                .{Activity/calendar_event_id}
            .{then}
                {Record/insert}
                    [Record/models]
                        Promise
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            resolve
                        [Function/out]
                            {Dialog/confirm}
                                [0]
                                    {Locale/text}
                                        The activity is linked to a meeting. Deleting it will remove the meeting as well. Do you want to proceed?   
                                [1]
                                    [confirm_callback]
                                        @resolve
                                        .{Function/call}
            {if}
                {Record/exists}
                    @record
                .{isFalsy}
            .{then}
                {break}
            @original
`;
