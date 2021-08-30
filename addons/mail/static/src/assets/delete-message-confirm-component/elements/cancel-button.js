/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            cancelButton
        [Element/model]
            DeleteMessageConfirmDialogComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-secondary
        [web.Element/textContent]
            {Locale/text}
                Delete
        [Element/onClick]
            {DeleteMessageConfirmView/onClickCancel}
            [0]
                @record
                .{DeleteMessageConfirmDialogComponent/deleteMessageConfirmView}
            [1]
                @ev
`;
