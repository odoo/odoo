/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            dialogOwner
        [Field/model]
            DeleteMessageConfirmView
        [Field/type]
            one
        [Field/target]
            Dialog
        [Field/isRequired]
            true
        [Field/isReadonly]
            true
        [Field/inverse]
            Dialog/deleteMessageConfirmView
`;
