/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            inlineText
        [Element/model]
            NotificationRequestComponent
        [web.Element/tag]
            span
        [Record/models]
            NotificationListItemComponent/coreItem
            NotificationListItemComponent/inlineText
        [web.Element/textContent]
            {Locale/text}
                Enable desktop notifications to chat.
`;
