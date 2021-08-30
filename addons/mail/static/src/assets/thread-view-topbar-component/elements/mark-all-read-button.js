/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            markAllReadButton
        [Element/model]
            ThreadViewTopbarComponent
        [Element/isPresent]
             @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/thread}
            .{&}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
                .{ThreadViewTopbar/thread}
                .{=}
                    {Env/inbox}
        [web.Element/class]
            btn
            btn-secondary
        [web.Element/tag]
            button
        [web.Element/isDisabled]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/threadView}
            .{ThreadView/messages}
            .{Collection/length}
            .{=}
                0
        [Element/onClick]
            {ThreadViewTopbar/onClickInboxMarkAllAsRead}
                [0]
                    @record
                   .{ThreadViewTopbarComponent/threadViewTopbar}
                [1]
                    @ev
        [web.Element/textContent]
            {Locale/text}
                Mark all read
`;
