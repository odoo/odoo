/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            followersPartner
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Partner
        [Field/related]
            Thread/followers
            Follower/partner
`;
