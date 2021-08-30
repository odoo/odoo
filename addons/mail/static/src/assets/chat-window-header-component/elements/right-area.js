/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            rightArea
        [Element/model]
            ChatWindowHeaderComponent
        [Record/models]
            ChatWindowHeaderComponent/item
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/height]
                {scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/align-items]
                center
            [web.scss/margin-right]
                {scss/map-get}
                    {scss/$spacers}
                    0
            {web.scss/selector}
                [0]
                    &:last-child .o-ChatWindowHeaderComponent-command
                [1]
                    [web.scss/margin-right]
                        {scss/map-get}
                            {scss/$spacers}
                            0
                        {Dev/comment}
                            no margin for commands
`;
