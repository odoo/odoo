/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Updates the current suggestion list. This method should be called
        whenever the UI has to be refreshed following change in state.

        This method should ideally be a compute, but its dependencies are
        currently too complex to express due to accessing plenty of fields
        from all records of dynamic models.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerView/_updateSuggestionList
        [Action/params]
            record
                [type]
                    ComposerView
        [Action/behavior]
            {if}
                @record
                .{ComposerView/suggestionDelimiterPosition}
                .{=}
                    undefined
                .{|}
                    @record
                    .{ComposerView/suggestionSearchTerm}
                    .{=}
                        undefined
                .{|}
                    @record
                    .{ComposerView/suggestionModelName}
                    .{isFalsy}
            .{then}
                {break}
            :suggestedRecords
                {Suggestion/searchSuggestions}
                    [0]
                        @record
                        .{ComposerView/suggestionModelName}
                    [1]
                        @record
                        .{ComposerView/suggestionSearchTerm}
                    [2]
                        [thread]
                            @record
                            .{ComposerView/composer}
                            .{Composer/activeThread}
            :mainSuggestedRecords
                @suggestedRecords
                .{Collection/first}
            :extraSuggestedRecords
                @suggestedRecords
                .{Collection/second}
            :sortFunction
                {Suggestion/getSuggestionSortFunction}
                    [0]
                        @record
                        .{ComposerView/suggestionModelName}
                    [1]
                        @record
                        .{ComposerView/suggestionSearchTerm}
                    [2]
                        [thread]
                            @record
                            .{ComposerView/composer}
                            .{Composer/activeThread}
            {Collection/sort}
                [0]
                    @mainSuggestedRecords
                [1]
                    @sortFunction
            {Collection/sort}
                [0]
                    @extraSuggestedRecords
                [1]
                    @sortFunction
            {Dev/comment}
                arbitrary limit to avoid displaying too many elements at once
                ideally a load more mechanism should be introduced
            :limit
                8
            {Record/update}
                [0]
                    @mainSuggestedRecords
                [1]
                    [Collection/length]
                        {Math/min}
                            [0]
                                @mainSuggestedRecords
                                .{Collection/length}
                            [1]
                                @limit
            {Record/update}
                [0]
                    @extraSuggestedRecords
                [1]
                    [Collection/length]
                        {Math/min}
                            [0]
                                @extraSuggestedRecords
                                .{Collection/length}
                            [1]
                                @limit
                                .{-}
                                    @mainSuggestedRecords
                                    .{Collection/length}
            {Record/update}
                [0]
                    @record
                [1]
                    [ComposerView/extraSuggestedRecords]
                        @extraSuggestedRecords
                    [ComposerView/hasToScrollToActiveSuggestion]
                        true
                    [ComposerView/mainSuggestedRecords]
                        @mainSuggestedRecords
`;
