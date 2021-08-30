/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            addressInfo
        [Field/model]
            TestAddress
        [Field/type]
            attr
`;
