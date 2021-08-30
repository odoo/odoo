/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/feature]
            snailmail
        [Field/name]
            messageViewOwnerAsSnailmailError
        [Field/model]
            Dialog
        [Field/type]
            one
        [Field/target]
            MessageView
        [Field/isReadonly]
            true
        [Field/inverse]
            MessageView/snailmailErrorDialog
`;
