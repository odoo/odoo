/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            addFollowersButton
        [Element/model]
            FollowerListMenuComponent
        [web.Element/tag]
            a
        [web.Element/class]
            dropdown-item
        [Element/isPresent]
            @record
            .{FollowerListMenuComponent/thread}
            .{Thread/channelType}
            .{!=}
                chat
        [web.Element/href]
            #
        [web.Element/role]
            menuitem
        [Element/onClick]
            {web.Event/preventDefault}
                @ev
            {FollowerListMenuComponent/_hide}
                @record
            {Thread/promptAddFollower}
                @record
                .{FollowerListMenuComponent/thread}
        [web.Element/textContent]
            {Locale/text}
                Add Followers
`;
