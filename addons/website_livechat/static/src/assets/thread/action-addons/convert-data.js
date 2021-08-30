/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/action]
            Thread/convertData
        [ActionAddon/feature]
            website_livechat
        [ActionAddon/params]
            data
        [ActionAddon/behavior]
            :data2
                @original
            {if}
                @data
                .{Dict/get}
                    visitor
            .{then}
                {if}
                    @data
                    .{Dict/get}
                        visitor
                .{then}
                    {Record/update}
                        [0]
                            @data2
                        [1]
                            [Thread/visitor]
                                {Record/insert}
                                    [Record/models]
                                        Visitor
                                    {Visitor/convertData}
                                        @data
                                        .{Dict/get}
                                            visitor
                .{else}
                    {Record/update}
                        [0]
                            @data2
                        [1]
                            [Thread/visitor]
                                {Record/empty}
            @data2
`;
