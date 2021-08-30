/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            channelGroups
        [Element/model]
            ThreadIconComponent
        [web.Element/class]
            fa
            fa-hashtag
        [Element/isPresent]
            @record
            .{ThreadIconComponent/thread}
            .{Thread/channelType}
            .{=}
                channel
            .{&}
                @record
                .{ThreadIconComponent/thread}
                .{Thread/public}
                .{=}
                    groups
        [web.Element/title]
            {Locale/text}
                Selected group of users
`;
