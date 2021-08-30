/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Updates the suggestion state based on the currently saved composer
        state (in particular content and cursor position).
    {onChange}
        [onChange/name]
            _onChangeUpdateSuggestionList
        [onChange/model]
            ComposerView
        [onChange/dependencies]
            ComposerView/suggestionDelimiterPosition
            ComposerView/suggestionModelName
            ComposerView/suggestionSearchTerm
            ComposerView/composer
                Composer/activeThread
        [onChange/behavior]
            {if}
                {Env/isCurrentUserGuest}
            .{then}
                {break}
            {Dev/comment}
                Update the suggestion list immediately for a reactive UX...
            {ComposerView/_updateSuggestionList}
                @record
            {Dev/comment}
                ...and then update it again after the server returned data.
            {ComposerView/_executeOrQueueFunction}
                [0]
                    @record
                [1]
                    {if}
                        {Record/exists}
                            @record
                        .{isFalsy}
                        .{|}
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
                        {Dev/comment}
                            ignore obsolete call
                        {break}
                    const Model = this.messaging.models[this.suggestionModelName];
                    :searchTerm
                        @record
                        .{ComposerView/suggestionSearchTerm}
                    {Record/doAsync}
                        [0]
                            @record
                        [1]
                            {Suggestion/fetchSuggestions}
                                [0]
                                    @record
                                    .{ComposerView/suggestionModelName}
                                [1]
                                    @searchTerm
                                [2]
                                    [thread]
                                        @record
                                        .{ComposerView/composer}
                                        .{Composer/activeThread}
                    {if}
                        {Record/exists}
                            @record
                        .{isFalsy}
                    .{then}
                        {break}
                    {ComposerView/_updateSuggestionList}
                        @record
                    {if}
                        @record
                        .{ComposerView/suggestionSearchTerm}
                        .{&}
                            @record
                            .{ComposerView/suggestionSearchTerm}
                            .{=}
                                @searchTerm
                        .{&}
                            @record
                            .{ComposerView/suggestionModelName}
                        .{&}
                            @record
                            .{ComposerView/hasSuggestions}
                            .{isFalsy}
                    .{then}
                        {ComposerView/closeSuggestions}
                            @record
`;