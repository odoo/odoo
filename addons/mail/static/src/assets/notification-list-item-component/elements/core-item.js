/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            coreItem
        [Element/model]
            NotificationListItemComponent
        [web.Element/style]
            [web.scss/margin]
                [0]
                    {scss/map-get}
                        {scss/$spacers}
                        0
                [1]
                    {scss/map-get}
                        {scss/$spacers}
                        2
            {web.scss/selector}
                [0]
                    &:first-child
                [1]
                    [web.scss/margin-inline-start]
                        {scss/map-get}
                            {scss/$spacers}
                            0
            {web.scss/selector}
                [0]
                    &:last-child
                [1]
                    [web.scss/margin-inline-end]
                        {scss/map-get}
                            {scss/$spacers}
                            0
`;
