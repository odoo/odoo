/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/feature]
            snailmail
        [Field/name]
            snailmailErrorDialog
        [Field/model]
            SnailmailErrorView
        [Field/type]
            one
        [Field/target]
            Dialog
        [Field/isCausal]
            true
        [Field/inverse]
            Dialog/messageViewOwnerAsSnailmailError
`;
