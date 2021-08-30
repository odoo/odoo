/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            channelPublic
        [Element/model]
            ThreadIconComponent
        [web.Element/class]
            fa
            fa-globe
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
                    public
        [web.Element/title]
            {Locale/text}
                Public channel
`;
