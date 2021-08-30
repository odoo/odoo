/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            dropdownMenuHeader
        [Element/model]
            MessagingMenuComponent
        [Element/isPresent]
            {Messaging/isInitialized}
        [web.Element/style]
            {if}
                {Device/isMobile}
                .{isFalsy}
            .{then}
                [web.scss/display]
                    flex
                [web.scss/flex-shrink]
                    0
                    {Dev/comment}
                        Forces Safari to not shrink below fit content
            {if}
                {Device/isMobile}
            .{then}
                [web.scss/display]
                    grid
                [web.scss/grid-template-areas]
                    [0]
                        top
                    [1]
                        bottom
                [web.scss/grid-template-rows]
                    auto
                    auto
                [web.scss/padding]
                    {scss/map-get}
                        {scss/$spacers}
                        2
            [web.scss/border-bottom]
                {scss/$border-width}
                solid
                {scss/gray}
                    400
            [web.scss/z-index]
                1
`;
