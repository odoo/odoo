/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            imageContainer
        [Element/model]
            DiscussSidebarCategoryItemComponent
        [web.Element/style]
            [web.scss/position]
                relative
            [web.scss/width]
                {scss/$o-mail-discuss-sidebar-category-item-avatar-size}
            [web.scss/height]
                {scss/$o-mail-discuss-sidebar-category-item-avatar-size}
`;
