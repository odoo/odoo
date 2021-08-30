/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            state
        [Field/model]
            Activity
        [Field/type]
            attr
`;
