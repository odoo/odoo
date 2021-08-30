/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onUpdate
        [Lifecycle/model]
            ComposerSuggestionComponent
        [Lifecycle/behavior]
            {if}
                @record
                .{ComposerSuggestionComponent/composerView}
                .{&}
                    @record
                    .{ComposerSuggestionComponent/composerView}
                    .{ComposerView/hasToScrollToActiveSuggestion}
                .{&}
                    @record
                    .{ComposerSuggestionComponent/isActive}
            .{then}
                {Record/scrollIntoView}
                    [0]
                        @record
                        .{ComposerSuggestionComponent/root}
                    [1]
                        [block]
                            center
                {Record/update}
                    [0]
                        @record
                        .{ComposerSuggestionComponent/composerView}
                    [1]
                        [ComposerView/hasToScrollToActiveSuggestion]
                            false
`;
