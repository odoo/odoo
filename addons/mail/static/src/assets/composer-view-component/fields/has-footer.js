/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether composer should display a footer.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasFooter
        [Field/model]
            ComposerViewComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{ComposerViewComponent/hasThreadTyping}
            .{|}
                @record
                .{ComposerViewComponent/composerView}
                .{ComposerView/composer}
                .{Composer/attachments}
                .{Collection/length}
                .{>}
                    0
            .{|}
                @record
                .{ComposerViewComponent/composerView}
                .{ComposerView/messageViewInEditing}
            .{|}
                @record
                .{ComposerViewComponent/isCompact}
                .{isFalsy}
`;
