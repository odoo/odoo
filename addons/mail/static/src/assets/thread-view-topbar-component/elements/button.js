/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            button
        [Element/model]
            ThreadViewTopbarComponent
        [web.Element/tag]
            button
        [web.Element/style]
            [web.scss/background]
                none
            [web.scss/border]
                none
            [web.scss/outline]
                none
            {if}
                @field
                .{web.Element/isActive}
            .{then}
                [web.scss/color]
                    {scss/gray}
                        700
            .{else}
                [web.scss/color]
                    {scss/gray}
                        500
            {web.scss/include}
                {web.scss/hover-focus}
                    [web.scss/outline]
                        none
                    [web.scss/color]
                        {scss/gray}
                            600
`;
