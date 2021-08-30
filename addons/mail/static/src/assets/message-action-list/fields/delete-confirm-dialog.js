/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            deleteConfirmDialog
        [Field/model]
            MessageActionList
        [Field/type]
            one
        [Field/target]
            Dialog
        [Field/isCausal]
            true
        [Field/inverse]
            Dialog/messageActionListOwnerAsDeleteConfirm
`;
