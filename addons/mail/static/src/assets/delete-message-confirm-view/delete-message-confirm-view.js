/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            DeleteMessageConfirmView
        [Model/fields]
            component
            dialogOwner
            message
            messageView
        [Model/id]
            DeleteMessageConfirmView/dialogOwner
        [Model/actions]
            DeleteMessageConfirmView/containsElement
            DeleteMessageConfirmView/onClickCancel
            DeleteMessageConfirmView/onClickDelete
`;
