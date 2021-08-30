/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            item
        [Element/model]
            ChatWindowHeaderComponent
        [web.Element/style]
            [web.scss/margin]
                [0]
                    {scss/map-get}
                        {scss/$spacers}
                        0
                [1]
                    {scss/map-get}
                        {scss/$spacers}
                        1
            {web.scss/selector}
                [0]
                    &:first-child
                [1]
                    [web.scss/margin-left]
                        {scss/map-get}
                            {scss/$spacers}
                            3
            {web.scss/selector}
                [0]
                    &:first-child.o-ChatWindowHeaderComponent-command
                [1]
                    [web.scss/margin-left]
                        {scss/map-get}
                            {scss/$spacers}
                            0
                        {Dev/comment}
                            no margin for commands
`;
