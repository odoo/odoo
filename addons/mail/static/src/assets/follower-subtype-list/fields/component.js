/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
       States the OWL component of this follower subtype list.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            component
        [Field/model]
            FollowerSubtypeList
        [Field/type]
            attr
        [Field/target]
            FollowerSubtypeListComponent
        [Field/inverse]
            FollowerSubtypeListComponent/followerSubtypeList
`;
