/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Returns a sort function to determine the order of display of canned
        responses in the suggestion list.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            CannedResponse/getSuggestionSortFunction
        [Action/params]
            searchTerm
            [thread]
                [description]
                    prioritize result in the context of given thread

        [Action/behavior]
            :cleanedSearchTerm
                {Utils/cleanSearchTerm}
                    @searchTerm
            {Record/insert}
                [Record/models]
                    Function
                [Function/in]
                    item1
                    item2
                [Function/out]
                    :cleanedName1
                        {Utils/cleanSearchTerm}
                            @item1
                            .{CannedResponse/source}
                    :cleanedName2
                        {Utils/cleanSearchTerm}
                            @item2
                            .{CannedResponse/source}
                    {if}
                        cleanedName1
                        .{String/startsWith}
                            @cleanedSearchTerm
                        .{&}
                            @cleanedName2
                            .{String/startsWith}
                                @cleanedSearchTerm
                            .{isFalsy}
                    .{then}
                        -1
                    .{elif}
                        @cleanedName1
                        .{String/startsWith}
                            @cleanedSearchTerm
                        .{isFalsy}
                        .{&}
                            @cleanedName2
                            .{String/startsWith}
                                @cleanedSearchTerm
                    .{then}
                        1
                    .{elif}
                        @cleanedName1
                        .{<}
                            @cleanedName2
                    .{then}
                        -1
                    .{elif}
                        @cleanedName1
                        .{>}
                            @cleanedName2
                    .{then}
                        1
                    .{else}
                        @item1
                        .{CannedResponse/id}
                        .{-}
                            @item2
                            .{CannedResponse/id}
`;
