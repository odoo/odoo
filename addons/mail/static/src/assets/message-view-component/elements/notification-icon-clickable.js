/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            notificationIconClickable
        [Element/model]
            MessageViewComponent
        [web.Element/style]
            [web.scss/color]
                {scss/gray}
                    600
            [web.scss/cursor]
                pointer
`;
