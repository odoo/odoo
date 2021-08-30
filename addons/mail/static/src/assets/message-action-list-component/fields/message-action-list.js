/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messageActionList
        [Field/model]
            MessageActionListComponent
        [Field/type]
            one
        [Field/target]
            MessageActionList
        [Field/isRequired]
            true
`;
