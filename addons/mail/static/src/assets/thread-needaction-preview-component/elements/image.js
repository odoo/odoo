/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            image
        [Element/model]
            ThreadNeedactionPreviewComponent
        [web.Element/tag]
            img
        [Record/models]
            NotificationListItemComponent/image
        [web.Element/src]
            {ThreadNeedactionPreviewComponent/getImage}
                @record
        [web.Element/alt]
            {Locale/text}
                Thread Image
`;
