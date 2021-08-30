/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            type
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            String
`;
