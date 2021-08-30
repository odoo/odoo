/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            name
        [Element/model]
            NotificationListItemComponent
        [web.Element/class]
            text-truncate
        [web.Element/style]
            {if}
                {Device/isMobile}
            .{then}
                [web.scss/font-size]
                    1.1
                    em
`;
