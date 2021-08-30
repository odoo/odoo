/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            subject
        [Element/model]
            MessageViewComponent
        [web.Element/tag]
            p
        [web.Element/class]
            mx-2
            mb-1
        [Element/isPresent]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/message}
            .{Message/subject}
            .{&}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/isSubjectSimilarToOriginThreadName}
                .{isFalsy}
        [web.Element/textContent]
            {String/sprintf}
                [0]
                    {Locale/text}
                        Subject: %s
                [1]
                    @record
                    .{MessageViewComponent/messageView}
                    .{MessageView/message}
                    .{Message/subject}
        [web.Element/style]
            [web.scss/font-style]
                italic
`;
