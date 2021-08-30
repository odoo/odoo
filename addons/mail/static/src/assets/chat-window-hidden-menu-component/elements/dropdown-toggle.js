/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            dropdownToggle
        [Element/model]
            ChatWindowHiddenMenuComponent
        [web.Element/class]
            dropdown-toggle
            {if}
                {ChatWindowManager/isHiddenMenuOpen}
            .{then}
                show
        [Element/onClick]
            {if}
                @record
                .{ChatWindowHiddenMenuComponent/_wasMenuOpen}
            .{then}
                {ChatWindowManager/closeHiddenMenu}
            .{else}
                {ChatWindowManager/openHiddenMenu}
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            [web.scss/justify-content]
                center
            [web.scss/flex]
                1
                1
                auto
            [web.scss/max-width]
                {scss/map-get}
                    {scss/$sizes}
                    100
            {if}
                {ChatWindowManager/isHiddenMenuOpen}
            .{then}
                [web.scss/opacity]
                    0.5
`;
