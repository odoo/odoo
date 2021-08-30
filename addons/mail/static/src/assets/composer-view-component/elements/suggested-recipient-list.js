/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            suggestedRecipientList
        [Element/model]
            ComposerViewComponent
        [Field/target]
            ComposerSuggestedRecipientListComponent
        [Element/isPresent]
            @record
            .{ComposerViewComponent/hasFollowers}
            .{&}
                @record
                .{ComposerViewComponent/composerView}
                .{ComposerView/composer}
                .{Composer/isLog}
                .{isFalsy}
            .{&}
                @record
                .{ComposerViewComponent/composerView}
                .{Composer/messageViewInEditing}
                .{isFalsy}
        [ComposerSuggestedRecipientListComponent/thread]
            @record
            .{ComposerViewComponent/composerView}
            .{ComposerView/composer}
            .{Composer/activeThread}
`;
