/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            avatar
        [Element/model]
            FollowerComponent
        [web.Element/tag]
            img
        [web.Element/src]
            @record
            .{FollowerComponent/follower}
            .{Follower/partner}
            .{Partner/avatarUrl}
        [web.Element/alt]
            {Locale/text}
                Avatar
        [web.Element/style]
            [web.scss/width]
                24
                px
            [web.scss/height]
                24
                px
            [web.scss/margin-inline-end]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/border-radius]
                50%
`;
