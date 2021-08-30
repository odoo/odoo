/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            dropdownMenu
        [Element/model]
            MessagingMenuComponent
        [web.Element/class]
            dropdown-menu
            dropdown-menu-right
        [Element/isPresent]
            @record
            .{MessagingMenuComponent/messagingMenu}
            .{MessagingMenu/isOpen}
        [web.Element/role]
            menu
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-flow]
                column
            [web.scss/padding-top]
                {scss/map-get}
                    {scss/$spacers}
                    0
            [web.scss/padding-bottom]
                {scss/map-get}
                    {scss/$spacers}
                    0
            [web.scss/overflow-y]
                auto
            {Dev/comment}
                Override from bootstrap .dropdown-menu to fix top alignment with other
                systray menu.
            [web.scss/margin-top]
                {scss/map-get}
                    {scss/$spacers}
                    0
            {if}
                {Messaging/isInitialized}
                .{isFalsy}
            .{then}
                [web.scss/align-items]
                    center
                [web.scss/justify-content]
                    center
            {if}
                {Device/isMobile}
                .{isFalsy}
            .{then}
                [web.scss/flex]
                    0
                    1
                    auto
                [web.scss/width]
                    350
                    px
                [web.scss/min-height]
                    50
                    px
                {Dev/comment}
                    Note: Min() refers to CSS min() and not SCSS min().

                    We want CSS min() and not SCSS min() because the former supports calc while the latter doesn't.
                    To by-pass SCSS min() shadowing CSS min(), we rely on SCSS being case-sensitive while CSS isn't.
                    As a result, Min() is ignored by SCSS while CSS interprets as its min() function.
                [web.scss/max-height]
                    {web.scss/Min}
                        [0]
                            {web.scss/calc}
                                100vh
                                .{-}
                                    140px
                        [1]
                            630px
                [web.scss/z-index]
                    1100
                    {Dev/comment}
                        on top of chat windows
            {if}
                {Device/isMobile}
            .{then}
                [web.scss/flex]
                    1
                    1
                    auto
                [web.scss/position]
                    fixed
                [web.scss/top]
                    {scss/$o-mail-chat-window-header-height-mobile}
                [web.scss/bottom]
                    0
                [web.scss/left]
                    0
                [web.scss/right]
                    0
                [web.scss/width]
                    {scss/map-get}
                        {scss/$sizes}
                        100
                [web.scss/margin]
                    0
                [web.scss/max-height]
                    none
                [web.scss/border]
                    0
`;
