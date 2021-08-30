/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the unfollow button is highlighted or not.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isUnfollowButtonHighlighted
        [Field/model]
            FollowButtonComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
