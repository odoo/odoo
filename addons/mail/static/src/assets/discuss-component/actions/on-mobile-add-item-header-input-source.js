/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussComponent/_onMobileAddItemHeaderInputSource
        [Action/params]
            record
            req
            res
        [Action/behavior]
            {if}
                @record
                .{DiscussComponent/discussView}
                .{DiscussView/discuss}
                .{Discuss/isAddingChannel}
            .{then}
                {Discuss/handleAddChannelAutocompleteSource}
                    [0]
                        @record
                        .{DiscussComponent/discussView}
                        .{DiscussView/discuss}
                    [1]
                        @req
                    [2]
                        @res
            .{else}
                {Discuss/handleAddChatAutocompleteSource}
                    [0]
                        @record
                        .{DiscussComponent/discussView}
                        .{DiscussView/discuss}
                    [1]
                        @req
                    [2]
                        @res
`;
