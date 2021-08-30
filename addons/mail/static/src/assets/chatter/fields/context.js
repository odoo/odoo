/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            context
        [Field/model]
            Chatter
        [Field/type]
            attr
        [Field/target]
            Object
`;
