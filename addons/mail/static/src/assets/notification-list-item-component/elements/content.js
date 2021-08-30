/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            content
        [Element/model]
            NotificationListItemComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-flow]
                column
            [web.scss/flex]
                1
                1
                auto
            [web.scss/align-self]
                flex-start
            [web.scss/min-width]
                0
                {Dev/comment}
                    needed for flex to work correctly
            [web.scss/margin]
                {scss/map-get}
                    {scss/$spacers}
                    2
`;
