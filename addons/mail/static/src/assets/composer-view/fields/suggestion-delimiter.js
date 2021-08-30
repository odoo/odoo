/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States which type of suggestion is currently in progress, if any.
        The value of this field contains the magic char that corresponds to
        the suggestion currently in progress, and it must be one of these:
        canned responses (:), channels (#), commands (/) and partners (@)
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            suggestionDelimiter
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
                        .{Composer/textInputContent}
                        .{Collection/length}
            .{then}
                {Record/empty}
            .{else}
                @record
                .{ComposerView/composer}
                .{Composer/textInputContent
                .{Collection/at}
                    @record
                    .{ComposerView/suggestionDelimiterPosition}
`;
