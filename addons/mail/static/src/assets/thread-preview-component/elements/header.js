/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            header
        [Element/model]
            ThreadPreviewComponent
        [Record/models]
            NotificationListItemComponent/header
        [web.Element/class]
            align-items-baseline
`;
