/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            deleteButton
        [Element/model]
            DeleteMessageConfirmDialogComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-primary
            me-2
        [web.Element/textContent]
            {Locale/text}
                Delete
        [Element/onClick]
            {DeleteMessageConfirmView/onClickDelete}
                [0]
                    @record
                    .{DeleteMessageConfirmDialogComponent/deleteMessageConfirmView}
                [1]
                    @ev
`;
