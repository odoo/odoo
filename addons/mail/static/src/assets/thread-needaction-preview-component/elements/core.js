/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            core
        [Element/model]
            ThreadNeedactionPreviewComponent
        [Record/models]
            NotificationListItemComponent/core
`;
