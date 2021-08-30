/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mailboxHistory
        [Element/model]
            ThreadIconComponent
        [web.Element/class]
            fa
            fa-history
        [Element/isPresent]
            @record
            .{ThreadIconComponent/thread}
            .{&}
                @record
                .{ThreadIconComponent/thread}
                .{Thread/model}
                .{=}
                    mail.box
            .{&}
                @record
                .{ThreadIconComponent/thread}
                .{=}
                    {Env/history}
`;
