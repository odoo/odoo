/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            contact
        [Field/model]
            TestAddress
        [Field/type]
            one
        [Field/target]
            TestContact
        [Field/inverse]
            address
`;
