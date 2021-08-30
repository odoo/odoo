/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            DiscussComponent
        [web.Element/class]
            {if}
                {Discuss/isAddingChannel}
                .{|}
                    {Discuss/isAddingChat}
            .{then}
                o-isAddingItem
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/height]
                {scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/min-height]
                0
            {if}
                {Device/isMobile}
            .{then}
                [web.scss/flex-flow]
                    column
                [web.scss/align-items]
                    center
                [web.scss/background-color]
                    {scss/$white}
`;
