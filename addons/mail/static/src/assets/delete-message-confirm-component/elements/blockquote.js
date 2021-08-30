/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            blockquote
        [Element/model]
            DeleteMessageConfirmDialogComponent
        [web.Element/tag]
            blockquote
        [web.Element/class]
            mx-3
            mb-3
        [web.Element/style]
            [scss/font-style]
                normal
        [web.Element/textContent]
            {Record/insert}
                [Record/models]
                    Element
                [Element/name]
                    message
                [Field/model]
                    DeleteMessageConfirmDialogComponent
                [Field/target]
                    MessageViewComponent
                [MessageViewComponent/messageView]
                    @record
                    .{DeleteMessageConfirmDialogComponent/deleteMessageConfirmView}
                    .{DeleteMessageConfirmView/messageview}
                [MessageViewComponent/showActions]
                    false
`;
