/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        In case the activity is linked to a meeting, we want to open the calendar
        view instead.
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/feature]
            calendar
        [ActionAddon/action]
            Activity/reschedule
        [ActionAddon/behavior]
            {if}
                @record
                .{Activity/calendarEventId}
                .{isFalsy}
            .{then}
                {break}
            .{else}
                :action
                    {Record/doAsync}
                        [0]
                            @record
                        [1]
                            @env
                            .{Env/owlEnv}
                            .{Dict/get}
                                services
                            .{Dict/get}
                                rpc
                            .{Function/call}
                                [model]
                                    mail.activity
                                [method]
                                    action_create_calendar_event
                                [args]
                                    {Record/insert}
                                        [Record/models]
                                            Collection
                                        {Record/insert}
                                            [Record/models]
                                                Collection
                                            @record
                                            .{Activity/id}
                @env
                .{Env/owlEnv}
                .{Dict/get}
                    bus
                .{Dict/get}
                    trigger
                .{Function/call}
                    [0]
                        do-action
                    [1]
                        @action
`;
