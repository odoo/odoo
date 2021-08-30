/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        HTML element that is used as anchor position for this popover view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            anchorRef
        [Field/model]
            PopoverView
        [Field/type]
            attr
        [Field/target]
            Element
        [Field/required]
            true
        [Field/compute]
            {if}
                @record
                .{PopoverView/threadViewTopbarOwnerAsInvite}
            .{then}
                @record
                .{PopoverView/threadViewTopbarOwnerAsInvite}
                .{ThreadViewTopbar/inviteButtonRef}
            .{elif}
                @record
                .{PopoverView/composerViewOwnerAsEmoji}
            .{then}
                @record
                .{PopoverView/composerViewOwnerAsEmoji}
                .{ComposerView/buttonEmojisRef}
            .{elif}
                @record
                .{PopoverView/messageActionListOwnerAsReaction}
            .{then}
                @record
                .{PopoverView/messageActionListOwnerAsReaction}
                .{MessageActionList/actionReactionRef}
            .{else}
                {Record/empty}
`;
