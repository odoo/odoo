/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            noImStatus
        [Element/model]
            ThreadIconComponent
        [web.Element/class]
            fa
            fa-question-circle
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
                .{Thread/orderedOtherTypingMembers}
                .{Collection/length}
                .{=}
                    0
            .{&}
                @record
                .{ThreadIconComponent/thread}
                .{Thread/correspondent}
                .{Partner/imStatus}
                .{isFalsy}
            .{&}
                @record
                .{ThreadIconComponent/thread}
                .{Thread/correspondent}
                .{!=}
                    {Env/partnerRoot}
        [web.Element/title]
            {Locale/text}
                No IM status available
`;
