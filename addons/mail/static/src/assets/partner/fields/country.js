/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            country
        [Field/model]
            Partner
        [Field/type]
            one
        [Field/target]
            Country
`;
