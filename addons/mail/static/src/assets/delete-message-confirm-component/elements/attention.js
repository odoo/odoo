/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            attention
        [Element/model]
            DeleteMessageConfirmDialogComponent
        [web.Element/tag]
            small
        [web.Element/class]
            mx-3
            mb-3
        [Element/isPresent]
            @record
            .{DeleteMessageConfirmDialogComponent/deleteMessageConfirmView}
            .{DeleteMessageConfirmView/message}
            .{Message/originThread}
            .{isFalsy}
            .{|}
                @record
                .{DeleteMessageConfirmDialogComponent/deleteMessageConfirmView}
                .{DeleteMessageConfirmView/message}
                .{Message/originThread}
                .{Thread/model}
                .{!=}
                    mail.channel
        [web.Element/textContent]
            {Locale/text}
                Pay attention: The followers of this document who were notified by email will still be able to read the content of this message and reply to it.
`;
