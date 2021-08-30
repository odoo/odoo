/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussSidebarCategory/onAddItemAutocompleteSource
        [Action/params]
            req
                [type]
                    Object
                [description]
                    @param {string} req.term
            res
                [type]
                    function
            record
                [type]
                    DiscussSidebarCategory
        [Action/behavior]
            {switch}
                @record
                .{DiscussSidebarCategory/autocompleteMethod}
            .{case}
                [channel]
                    {Discuss/handleAddChannelAutocompleteSource}
                        @req
                        @res
                [chat]
                    {Discuss/handleAddChatAutocompleteSource}
                        @req
                        @res
`;
