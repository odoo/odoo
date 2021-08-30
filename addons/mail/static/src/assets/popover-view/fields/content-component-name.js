/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the component name of the content.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            contentComponentName
        [Field/model]
            PopoverView
        [Field/type]
            attr
        [Field/target]
            String
        [Field/default]
            {String/empty}
        [Field/isRequired]
            true
        [Field/compute]
            {if}
                @record
                .{PopoverView/channelInvitationForm}
            .{then}
                ChannelInvitationFormComponent
            .{elif}
                @record
                .{PopoverView/emojiListView}
            .{then}
                EmojiListComponent
            .{else}
                {Record/empty}
`;
