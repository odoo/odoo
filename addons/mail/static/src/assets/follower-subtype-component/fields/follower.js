/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            follower
        [Field/model]
            FollowerSubtypeComponent
        [Field/type]
            one
        [Field/target]
            Follower
        [Field/isRequired]
            true
`;
