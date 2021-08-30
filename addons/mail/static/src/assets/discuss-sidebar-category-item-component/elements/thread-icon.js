/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            threadIcon
        [Element/model]
            DiscussSidebarCategoryItemComponent
        [Element/isPresent]
            @record
            .{DiscussSidebarCategoryItemComponent/categoryItem}
            .{DiscussSidebarCategoryItem/hasThreadIcon}
        [Field/target]
            ThreadIconComponent
        [ThreadIconComponent/thread]
            @record
            .{DiscussSidebarCategoryItemComponent/categoryItem}
            .{DiscussSidebarCategoryItem/channel}
        [web.Element/style]
            {web.scss/include}
                {scss/o-position-absolute}
                    [$bottom]
                        0
                    [$right]
                        0
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            [web.scss/justify-content]
                center
            [web.scss/width]
                13
                px
            [web.scss/height]
                13
                px
            [web.scss/font-size]
                xx-small
            [web.scss/background-color]
                {scss/gray}
                    100
            [web.scss/border-radius]
                50%
`;
