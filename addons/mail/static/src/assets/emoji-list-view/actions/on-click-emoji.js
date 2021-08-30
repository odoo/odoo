/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            EmojiListView/onClickEmoji
        [Action/params]
            ev
                [type]
                    web.MouseEvent
            record
                [type]
                    EmojiListView
        [Action/behavior]
            {if}
                @record
                .{EmojiListView/popoverViewOwner}
                .{PopoverView/messageActionListOwnerAsReaction}
            .{then}
                {MessageActionList/onClickReaction}
                    [0]
                        @record
                        .{EmojiListView/popoverViewOwner}
                        .{PopoverView/messageActionListOwnerAsReaction}
                    [1]
                        @ev
            .{elif}
                @record
                .{EmojiListView/popoverViewOwner}
                .{PopoverView/composerViewOwnerAsEmoji}
            .{then}
                {ComposerView/onClickEmoji}
                    [0]
                        @record
                        .{EmojiListView/popoverViewOwner}
                        .{PopoverView/composerViewOwnerAsEmoji}
                    [1]
                        @ev
`;
