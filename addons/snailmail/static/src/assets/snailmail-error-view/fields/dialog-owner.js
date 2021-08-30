/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            dialogOwner
        [Field/model]
            SnailmailErrorView
        [Field/type]
            one
        [Field/target]
            Dialog
        [Field/inverse]
            Dialog/snailmailErrorView
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
`;
