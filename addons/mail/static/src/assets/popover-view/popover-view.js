/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            PopoverView
        [Model/fields]
            anchorRef
            channelInvitationForm
            component
            composerViewOwnerAsEmoji
            content
            contentClassName
            contentComponentName
            device
            emojiListView
            messageActionListOwnerAsReaction
            position
            threadViewTopbarOwnerAsInvite
        [Model/id]
            PopoverView/threadViewTopbarOwner
            .{&}
                PopoverView/channelInvitationForm
        [Model/actions]
            PopoverView/_onClickCaptureGlobal
            PopoverView/contains
`;
