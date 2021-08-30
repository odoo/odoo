/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            FollowButtonComponent
        [Model/fields]
            isDisabled
            isUnfollowButtonHighlighted
            thread
        [Model/template]
            root
                unfollow
                    unfollowIcon
                    unfollowLabel
                    followingIcon
                    followingLabel
                follow
`;
