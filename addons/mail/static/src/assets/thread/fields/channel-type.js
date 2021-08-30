/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            channelType
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            String
`;
