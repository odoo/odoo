/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Discuss/handleAddChatAutocompleteSource
        [Action/params]
            discuss
            req
            res
        [Action/behavior]
            {Partner/imSearch}
                [callback]
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            partners
                        [Function/out]
                            :suggestions
                                @partners
                                .{Collection/map}
                                    {Record/insert}
                                        [Record/models]
                                            Function
                                        [Function/in]
                                            item
                                        [Function/out]
                                            {Record/insert}
                                                [Record/models]
                                                    Dict
                                                [id]
                                                    @partner
                                                    .{Partner/id}
                                                [value]
                                                    @partner
                                                    .{Partner/nameOrDisplayName}
                                                [label]
                                                    @partner
                                                    .{Partner/nameOrDisplayName}
                            @res
                                {Collection/sortBy}
                                    [0]
                                        @suggestions
                                    [1]
                                        label
                [keyword]
                    {String/escape}
                        @req
                        .{Dict/get}
                            term
                [limit]
                    10
`;
