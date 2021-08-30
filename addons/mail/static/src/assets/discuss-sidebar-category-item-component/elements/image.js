/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            image
        [Element/model]
            DiscussSidebarCategoryItemComponent
        [web.Element/tag]
            img
        [web.Element/class]
            rounded-circle
        [web.Element/src]
            @record
            .{DiscussSidebarCategoryItemComponent/categoryItem}
            .{DiscussSidebarCategoryItem/avatarUrl}
        [web.Element/alt]
            {Locale/text}
                Thread image
        [web.Element/style]
            [web.scss/object-fit]
                cover
            [web.scss/width]
                {scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/height]
                {scss/map-get}
                    {scss/$sizes}
                    100
`;
