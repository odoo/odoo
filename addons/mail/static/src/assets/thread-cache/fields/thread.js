/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            thread
        [Field/model]
            ThreadCache
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/inverse]
            Thread/cache
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
`;
