/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            discussView
        [Field/model]
            Discuss
        [Field/type]
            one
        [Field/target]
            DiscussView
        [Field/isCausal]
            true
        [Field/inverse]
            DiscussView/discuss
`;
