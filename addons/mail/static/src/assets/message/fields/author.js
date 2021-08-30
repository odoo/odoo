/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            author
        [Field/model]
            Message
        [Field/type]
            one
        [Field/target]
            Partner
`;
