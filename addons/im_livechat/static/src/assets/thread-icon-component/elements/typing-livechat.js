/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            typingLivechat
        [Element/feature]
            im_livechat
        [Element/model]
            ThreadIconComponent
        [Field/target]
            ThreadTypingIconComponent
        [Record/models]
            ThreadTypingIcon/typing
        [Element/isPresent]
            @record
            .{ThreadIconComponent/thread}
            .{Thread/channelType}
            .{=}
                livechat
            .{&}
                @record
                .{ThreadIconComponent/thread}
                .{Thread/orderedOtherTypingMembers}
                .{Collection/length}
                .{>}
                    0
        [ThreadTypingIconComponent/animation]
            pulse
        [ThreadTypingIconComponent/title]
            @record
            .{ThreadIconComponent/thread}
            .{Thread/typingStatusText}
`;
