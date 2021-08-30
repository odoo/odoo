/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            list
        [Element/model]
            ChatWindowHiddenMenuComponent
        [web.Element/tag]
            ul
        [web.Element/class]
            dropdown-menu
            dropdown-menu-right
            {if}
                {ChatWindowManager/isHiddenMenuOpen}
            .{then}
                show
        [web.Element/role]
            menu
        [web.Element/style]
            [web.scss/overflow]
                auto
            [web.scss/margin]
                {web.scss/map-get}
                    {scss/$spacers}
                    0
            [web.scss/padding]
                {web.scss/map-get}
                    {scss/$spacers}
                    0
`;
