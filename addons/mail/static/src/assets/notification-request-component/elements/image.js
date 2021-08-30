/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            image
        [Element/model]
            NotificationRequestComponent
        [web.Element/tag]
            img
        [Record/models]
            NotificationListItemComponent/image
        [web.Element/class]
            rounded-circle
        [web.Element/src]
            /mail/static/src/img/odoobot.png
        [web.Element/alt]
            {Locale/text}
                Avatar of OdooBot
`;
