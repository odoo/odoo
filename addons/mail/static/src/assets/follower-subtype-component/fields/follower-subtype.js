/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            followerSubtype
        [Field/model]
            FollowerSubtypeComponent
        [Field/type]
            one
        [Field/target]
            FollowerSubtype
        [Field/isRequired]
            true
`;
