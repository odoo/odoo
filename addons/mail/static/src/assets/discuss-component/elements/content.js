/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            content
        [Element/model]
            DiscussComponent
        [Element/isPresent]
            {Device/isMobile}
            .{isFalsy}
        [web.Element/style]
            [web.scss/height]
                {scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/overflow]
                auto
            [web.scss/flex]
                1
                1
                auto
            [web.scss/display]
                flex
            [web.scss/flex-flow]
                column
`;
