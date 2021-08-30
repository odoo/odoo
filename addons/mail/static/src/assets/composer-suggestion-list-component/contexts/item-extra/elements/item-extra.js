/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            itemExtra
        [Element/model]
            ComposerSuggestionListComponent:itemExtra
        [Field/target]
            ComposerSuggestionComponent
        [ComposerSuggestionComponent/composerView]
            @record
            .{ComposerSuggestionListComponent/composerView}
        [ComposerSuggestionComponent/isActive]
            @record
            .{ComposerSuggestionListComponent:itemExtra/record}
            .{=}
                @record
                .{ComposerSuggestionListComponent/composerView}
                .{ComposerView/activeSuggestedRecord}
        [ComposerSuggestionComponent/modelName]
            @record
            .{ComposerSuggestionListComponent/composerView}
            .{ComposerView/suggestionModelName}
        [ComposerSuggestionComponent/record]
            @record
            .{ComposerSuggestionListComponent:itemExtra/record}
`;
