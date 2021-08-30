/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            cache
        [Field/model]
            Thread
        [Field/type]
            one
        [Field/target]
            ThreadCache
        [Field/inverse]
            thread
        [Field/isCausal]
            true
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/default]
            {Record/insert}
                [Record/models]
                    ThreadCache
`;
