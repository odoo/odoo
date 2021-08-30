/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Position of the popover view relative to its anchor point.
        Valid values: 'top', 'right', 'bottom', 'left'
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            position
        [Field/model]
            PopoverView
        [Field/type]
            attr
        [Field/target]
            String
        [Field/default]
            top
        [Field/compute]
            {if}
                @record
                .{PopoverView/threadViewTopbarOwnerAsInvite}
            .{then}
                bottom
            .{elif}
                @record
                .{PopoverView/composerViewOwnerAsEmoji}
            .{then}
                top
            .{elif}
                @record
                .{PopoverView/messageActionListOwnerAsReaction}
            .{then}
                top
            .{else}
                {Record/empty}
`;
