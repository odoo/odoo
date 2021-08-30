/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingMenuComponent/_onMobileNewMessageInputSource
        [Action/params]
            req
                [type]
                    Object
                [description]
                    @param {string} req.term
            res
                [type]
                    Function
        [Action/behavior]
            :value
                {String/escape}
                    @req
                    .{Dict/get}
                        term
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
                                            [id]
                                                @item
                                                .{Partner/id}
                                            [value]
                                                @item
                                                .{Partner/nameOrDisplayName}
                                            [label]
                                                @item
                                                .{Partner/nameOrDisplayName}
                            @res
                                {Collection/sortBy}
                                    [0]
                                        @suggestions
                                    [1]
                                        label
                [keyword]
                    @value
                [limit]
                    10
`;
