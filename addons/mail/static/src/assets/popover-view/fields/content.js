/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the record that is content of this popover view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            content
        [Field/model]
            PopoverView
        [Field/type]
            one
        [Field/target]
            Record
        [Field/isRequired]
            true
        [Field/compute]
            {if}
                @record
                .{PopoverView/channelInvitationForm}
            .{then}
                @record
                .{PopoverView/channelInvitationForm}
            .{elif}
                @record
                .{PopoverView/emojiListView}
            .{then}
                @record
                .{PopoverView/emojiListView}
            .{else}
                {Record/empty}
`;
