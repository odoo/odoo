/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            iconLivechat
        [Element/feature]
            im_livechat
        [Element/model]
            ThreadIconComponent
        [web.Element/class]
            fa
            fa-comments
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
                .{=}
                    0
        [web.Element/title]
            {Locale/text}
                Livechat
`;
