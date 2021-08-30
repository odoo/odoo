/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            subtypes
        [Field/model]
            Follower
        [Field/type]
            many
        [Field/target]
            FollowerSubtype
`;
