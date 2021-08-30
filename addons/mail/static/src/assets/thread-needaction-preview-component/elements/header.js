/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            header
        [Element/model]
            ThreadNeedactionPreviewComponent
        [Record/models]
            NotificationListItemComponent/header
`;
