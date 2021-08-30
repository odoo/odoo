/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            manager
        [Field/model]
            Dialog
        [Field/type]
            one
        [Field/target]
            DialogManager
        [Field/inverse]
            DialogManager/dialogs
        [Field/isReadonly]
            true
        [Field/compute]
            {Env/dialogManager}
`;
