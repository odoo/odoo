/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            dialog
        [Field/model]
            DialogManagerComponent:dialog
        [Field/type]
            one
        [Field/target]
            Dialog
        [Field/isRequired]
            true
`;
