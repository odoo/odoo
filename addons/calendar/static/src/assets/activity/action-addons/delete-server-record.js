/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/feature]
            calendar
        [ActionAddon/action]
            Activity/deleteServerRecord
        [ActionAddon/behavior]
            {if}
                @record
                .{Activity/calendarEventId}
                .{isFalsy}
            .{then}
                @original
            .{else}
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
                                unlink_w_meeting
                            [args]
                                {Record/insert}
                                    [Record/models]
                                        Collection
                                    {Record/insert}
                                        [Record/models]
                                            Collection
                                        @record
                                        .{Activity/id}
                {Record/delete}
                    @record
`;
