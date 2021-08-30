/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            notificationNonFailureIcon
        [Element/model]
            MessageViewComponent
        [Record/models]
            MessageViewComponent/notificationIcon
        [web.Element/name]
            notificationIcon
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-envelope-o
`;
