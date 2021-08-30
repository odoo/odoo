/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            followers
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Follower
        [Field/inverse]
            Follower/followedThread
`;
