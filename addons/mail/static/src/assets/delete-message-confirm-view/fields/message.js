/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            message
        [Field/model]
            DeleteMessageConfirmView
        [Field/type]
            one
        [Field/target]
            Message
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/compute]
            @record
            .{DeleteMessageConfirmView/dialogOwner}
            .{Dialog/messageActionListOwnerAsDeleteConfirm}
            .{MessageActionList/message}
`;
