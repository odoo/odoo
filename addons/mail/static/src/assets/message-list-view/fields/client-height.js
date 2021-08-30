/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            clientHeight
        [Field/model]
            MessageListView
        [Field/type]
            attr
        [Field/target]
            Integer
`;
