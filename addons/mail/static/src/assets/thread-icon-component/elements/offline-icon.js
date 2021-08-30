/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            offlineIcon
        [Element/model]
            ThreadIconComponent
        [Record/models]
            ThreadIconComponent/offline
        [web.Element/class]
            fa
            fa-circle-o
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
                .{Partner/imStatus}
                .{=}
                    offline
        [web.Element/title]
            {Locale/text}
                Offline
`;
