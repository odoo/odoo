/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            separator
        [Elenent/model]
            ComposerSuggestionListComponent
        [web.Element/class]
            dropdown-divider
        [Element/isPresent]
            @record
            .{ComposerSuggestionListComponent/composerView}
            .{ComposerView/mainSuggestedRecords}
            .{Collection/length}
            .{>}
                0
            .{&}
                @record
                .{ComposerSuggestionListComponent/composerView}
                .{ComposerView/extraSuggestedRecords}
                .{Collection/length}
                .{>}
                    0
        [web.Element/role]
            separator
`;
