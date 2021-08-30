/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            date
        [Element/model]
            NotificationListItemComponent
        [Record/models]
            NotificationListItemComponent/bold
        [web.Element/style]
            [web.scss/flex]
                0
                0
                auto
            [web.scss/font-size]
                x-small
            [web.scss/color]
                {scss/gray}
                    500
`;
