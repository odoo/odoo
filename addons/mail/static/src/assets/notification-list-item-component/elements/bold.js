/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            bold
        [Element/model]
            NotificationListItemComponent
        [web.Element/style]
            [web.scss/font-weight]
                bold
`;
