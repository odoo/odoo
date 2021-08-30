/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            recipients
        [Field/model]
            Message
        [Field/type]
            many
        [Field/target]
            Partner
`;
