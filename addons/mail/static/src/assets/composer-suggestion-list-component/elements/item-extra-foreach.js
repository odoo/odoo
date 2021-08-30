/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            itemExtraForeach
        [Element/model]
            ComposerSuggestionListComponent
        [Record/models]
            Foreach
        [Field/target]
            ComposerSuggestionListComponent:itemExtra
        [ComposerSuggestionListComponent:itemExtra/record]
            @field
            .{Foreach/get}
                record
        [Foreach/collection]
            @record
            .{ComposerSuggestionListComponent/composerView}
            .{ComposerView/extraSuggestedRecords}
        [Foreach/as]
            record
        [Element/key]
            @field
            .{Foreach/get}
                record
            .{Record/id}
`;
