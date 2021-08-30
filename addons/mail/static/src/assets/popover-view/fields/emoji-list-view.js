/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        If set, the content of this popover view is a list of emojis.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            emojiListView
        [Field/model]
            PopoverView
        [Field/type]
            one
        [Field/target]
            EmojiListView
        [Field/isCausal]
            true
        [Field/isReadonly]
            true
        [Field/inverse]
            EmojiListView/popoverViewOwner
        [Field./compute]
            {if}
                @record
                .{PopoverView/composerViewOwnerAsEmoji}
            .{then}
                {Record/insert}
                    [Record/models]
                        PopoverView
            .{elif}
                @record
                .{PopoverView/messageActionListOwnerAsReaction}
            .{then}
                {Record/insert}
                    [Record/models]
                        PopoverView
            .{else}
                {Record/empty}
`;
