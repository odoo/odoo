/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            image
        [Element/model]
            NotificationListItemComponent
        [web.Element/style]
            [web.scss/width]
                {scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/height]
                {scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/object-fit]
                cover
`;
