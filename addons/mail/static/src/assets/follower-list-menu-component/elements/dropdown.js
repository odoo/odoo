/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            dropdown
        [Element/model]
            FollowerListMenuComponent
        [web.Element/class]
            dropdown-menu
            dropdown-menu-right
        [Element/isPresent]
            @record
            .{FollowerListMenuComponent/isDropdownOpen}
        [web.Element/role]
            menu
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-flow]
                column
            {Dev/comment}
                Note: Min() refers to CSS min() and not SCSS min().

                To by-pass SCSS min() shadowing CSS min(), we rely on SCSS being case-sensitive while CSS isn't.
            [web.scss/max-width]
                {scss/Min}
                    400px
                    95vw
`;
