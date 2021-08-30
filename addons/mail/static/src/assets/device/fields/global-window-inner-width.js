/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            globalWindowInnerWidth
        [Field/model]
            Device
        [Field/type]
            attr
        [Field/target]
            Number
`;
