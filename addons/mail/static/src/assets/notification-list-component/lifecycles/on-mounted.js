/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onMounted
        [Lifecycle/model]
            NotificationListComponent
        [Lifecycle/behavior]
            {NotificationListComponent/_loadPreviews}
                @record
`;
