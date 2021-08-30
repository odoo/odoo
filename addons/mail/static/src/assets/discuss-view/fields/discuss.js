/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            discuss
        [Field/model]
            DiscussView
        [Field/type]
            one
        [Field/target]
            Discuss
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/inverse]
            Discuss/discussView
`;
