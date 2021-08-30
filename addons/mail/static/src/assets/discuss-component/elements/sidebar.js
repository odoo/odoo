/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            sidebar
        [Element/model]
            DiscussComponent
        [Field/target]
            DiscussSidebarComponent
        [DiscussSidebarComponent/discussView]
            {Discuss/discussView}
        [Element/isPresent]
            {Device/isMobile}
            .{isFalsy}
        [web.Element/class]
            bg-light
            border-right
        [web.Element/style]
            [web.scss/height]
                {scss/scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/overflow]
                auto
            [web.scss/padding-top]
                {scss/map-get}
                    {scss/$spacers}
                    3
            [web.scss/flex]
                0
                0
                auto
`;
