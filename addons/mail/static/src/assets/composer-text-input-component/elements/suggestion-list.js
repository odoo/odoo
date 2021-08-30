/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            suggestionList
        [Element/model]
            ComposerTextInputComponent
        [Field/target]
            ComposerSuggestionListComponent
        [Element/isPresent]
            @record
            .{ComposerTextInputComponent/composerView}
            .{ComposerView/hasSuggestions}
        [ComposerSuggestionListComponent/composerView]
            @record
            .{ComposerTextInputComponent/composerView}
        [ComposerSuggestionListComponent/isBelow]
            @record
            .{ComposerTextInputComponent/hasMentionSuggestionsBelowPosition}
`;
