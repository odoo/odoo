/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            address
        [Field/model]
            TestContact
        [Field/type]
            one
        [Field/target]
            TestAddress
        [Field/inverse]
            TestAddress/contact
`;
