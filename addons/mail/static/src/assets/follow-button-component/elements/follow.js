/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            follow
        [Element/model]
            FollowButtonComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-link
        [Element/isPresent]
            @record
            .{FollowButtonComponent/thread}
            .{Thread/isCurrentPartnerFollowing}
        [web.Element/isDisabled]
            @record
            .{FollowButtonComponent/isDisabled}
        [Element/onClick]
            {Thread/follow}
                @record
                .{FollowButtonComponent/thread}
        [web.Element/textContent]
            {Locale/text}
                Follow
        [web.Element/style]
            [web.scss/color]
                {scss/gray}
                    600
`;
