/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            partner
        [Field/model]
            Follower
        [Field/type]
            one
        [Field/target]
            Partner
        [Field/isRequired]
            true
`;
