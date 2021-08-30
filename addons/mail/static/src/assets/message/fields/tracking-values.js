/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            trackingValues
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            Array
`;
