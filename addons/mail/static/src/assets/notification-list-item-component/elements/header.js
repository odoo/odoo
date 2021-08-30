/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            header
        [Element/model]
            NotificationListItemComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/margin-bottom]
                {scss/map-get}
                    {scss/$spacers}
                    1
`;
