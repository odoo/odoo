/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Whether the message is "active", ie: hovered or clicked, and should
        display additional things (date in sidebar, message actions, etc.)
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isActive
        [Field/model]
            MessageViewComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{MessageViewComponent/isHovered}
            .{|}
                @record
                .{MessageViewComponent/isClicked}
            .{|}
                @record
                .{/messageView}
                .{/messageActionList}
                .{&}
                    @record
                    .{MessageViewComponent/messageView}
                    .{MessageView/messageActionList}
                    .{MessageActionList/reactionPopoverView}
                    .{|}
                        @record
                        .{MessageViewComponent/messageView}
                        .{MessageView/messageActionList}
                        .{MessageActionList/deleteConfirmDialog}
`;
