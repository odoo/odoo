/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            editButton
        [Element/model]
            FollowerComponent
        [web.Element/tag]
            button
        [Record/models]
            FollowerComponent/button
        [web.Element/class]
            btn
            btn-icon
        [Element/isPresent]
            @record
            .{FollowerComponent/follower}
            .{Follower/isEditable}
        [web.Element/title]
            {Locale/text}
                Edit subscription
        [Element/onClick]
            {web.Event/preventDefault}
                @ev
            {Follower/showSubtypes}
                @record
                .{FollowerComponent/follower}
`;
