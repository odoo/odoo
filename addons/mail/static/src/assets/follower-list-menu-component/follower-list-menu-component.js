/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            FollowerListMenuComponent
        [Model/fields]
            device
            isDisabled
            isDropdownOpen
            thread
        [Model/template]
            root
                followers
                    buttonFollowers
                        buttonFollowersIcon
                        buttonFollowersCount
                    dropdown
                        addFollowersButton
                        separator
                        followerForeach
        [Model/actions]
            FollowerListMenuComponent/_hide
`;
