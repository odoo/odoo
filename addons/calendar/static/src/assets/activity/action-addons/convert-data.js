/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/feature]
            calendar
        [ActionAddon/action]
            Activity/convertData
        [ActionAddon/behavior]
            :res
                @original
            {if}
                @data
                .{Dict/hasKey}
                    calendar_event_id
            .{then}
                {Record/update}
                    [0]
                        @res
                    [1]
                        @data
                        .{Dict/get}
                            calendar_event_id
                        .{Collection/first}
            @oroginal
`;
