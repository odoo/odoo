/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the composer should display a header.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasHeader
        [Field/model]
            ComposerViewComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {if}
                @record
                .{ComposerViewComponent/hasThreadName}
                .{&}
                    @record
                    .{ComposerViewComponent/composerView}
                    .{ComposerView/composer}
                    .{Composer/thread}
            .{then}
                true
            .{elif}
                @record
                .{ComposerViewComponent/hasFollowers}
                .{&}
                    @record
                    .{ComposerViewComponent/composerView}
                    .{ComposerView/composer}
                    .{Composer/isLog}
                    .{isFalsy}
            .{then}
                true
            {if}
                @record
                .{ComposerViewComponent/composerView}
                .{ComposerView/threadView}
                .{&}
                    @record
                    .{ComposerViewComponent/composerView}
                    .{ComposerView/threadView}
                    .{ThreadView/replyingToMessageView}
            .{then}
                true
            .{else}
                false
`;
