/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            botIcon
        [Element/model]
            ThreadIconComponent
        [Record/models]
            ThreadIconComponent/online
        [web.Element/class]
            fa
            fa-heart
        [Element/isPresent]
            @record
            .{ThreadIconComponent/thread}
            .{Thread/channelType}
            .{=}
                chat
            .{&}
                @record
                .{ThreadIconComponent/thread}
                .{Thread/correspondent}
            .{&}
                @record
                .{ThreadIconComponent/thread}
                .{Thread/correspondent}
                .{=}
                    {Env/partnerRoot}
        [web.Element/title]
            {Locale/text}
                Bot
`;
