/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            text
        [Element/model]
            NotificationAlertComponent
        [web.Element/tag]
            center
        [web.Element/class]
            alert
            alert-primary
        [Element/isPresent]
            {NotificationAlertComponent/isNotificationBlocked}
                @record
        [web.Element/textContent]
            {Locale/text}
                Odoo Push notifications have been blocked. Go to your browser settings to allow them.
`;
