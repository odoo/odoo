/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            imageContainer
        [Element/model]
            ThreadPreviewComponent
        [Record/models]
            NotificationListItemComponent/imageContainer
`;
