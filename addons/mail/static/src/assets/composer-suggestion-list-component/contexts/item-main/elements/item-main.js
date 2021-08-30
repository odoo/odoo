/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            itemMain
        [Element/model]
            ComposerSuggestionListComponent:itemMain
        [Field/target]
            ComposerSuggestionComponent
        [ComposerSuggestionComponent/composerView]
            @record
            .{ComposerSuggestionListComponent/composerView}
        [ComposerSuggestionComponent/isActive]
            @record
            .{ComposerSuggestionListComponent:itemMain/record}
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
            .{ComposerSuggestionListComponent:itemMain/record}
`;
