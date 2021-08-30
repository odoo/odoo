/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            channelPrivate
        [Element/model]
            ThreadIconComponent
        [web.Element/class]
            fa
            fa-lock
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
                    private
        [web.Element/title]
            {Locale/text}
                Private channel
`;
