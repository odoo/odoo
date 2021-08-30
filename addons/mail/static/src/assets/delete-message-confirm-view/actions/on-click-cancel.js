/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DeleteMessageConfirmView/onClickCancel
        [Action/params]
            record
                [type]
                    DeleteMessageConfirmView
        [Action/behavior]
            {Record/delete}
                @record
                .{DeleteMessageConfirmView/dialogOwner}
`;
