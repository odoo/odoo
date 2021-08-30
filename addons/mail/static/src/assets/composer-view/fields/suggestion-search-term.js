/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the search term to use for suggestions (if any).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            suggestionSearchTerm
        [Field/model]
            ComposerView
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{ComposerView/composer}
                .{isFalsy}
                .{|}
                    @record
                    .{ComposerView/suggestionDelimiterPosition}
                    .{=}
                        undefined
                .{|}
                    @record
                    .{ComposerView/suggestionDelimiterPosition}
                    .{>=}
                        @record
                        .{ComposerView/composer}
                        .{Composer/textInputCursorStart}
            .{then}
                {Record/empty}
            .{else}
                @record
                .{ComposerView/composer}
                .{Composer/textInputContent}
                .{String/substring}
                    [0]
                        @record
                        .{ComposerView/suggestionDelimiterPosition}
                        .{+}
                            1
                    [1]
                        @record
                        .{ComposerView/composer}
                        .{Composer/textInputCursorStart}
`;
