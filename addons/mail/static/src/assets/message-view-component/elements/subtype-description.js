/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            subtypeDescription
        [Element/model]
            MessageViewComponent
        [web.Element/tag]
            p
        [Element/isPresent]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/message}
            .{Message/subtypeDescription}
            .{&}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/isBodyEqualSubtypeDescription}
                .{isFalsy}
        [web.Element/textContent]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/message}
            .{Message/subtypeDescription}
`;
