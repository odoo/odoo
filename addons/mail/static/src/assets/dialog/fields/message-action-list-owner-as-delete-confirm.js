/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messageActionListOwnerAsDeleteConfirm
        [Field/model]
            Dialog
        [Field/type]
            one
        [Field/target]
            MessageActionList
        [Field/isReadonly]
            true
        [Field/inverse]
            MessageActionList/deleteConfirmDialog
`;
