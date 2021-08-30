/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            notificationFailureIcon
        [Element/model]
            MessageViewComponent
        [web.Element/tag]
            i
        [Record/models]
            MessageViewComponent/notificationIcon
        [web.Element/class]
            fa
            fa-envelope
`;
