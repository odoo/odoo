/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            icon
        [Element/model]
            RtcLayoutMenuComponent
        [web.Element/style]
            [web.scss/width]
                5rem
            [web.scss/height]
                5rem
            [web.scss/margin-inline-end]
                {scss/map-get}
                    {scss/$spacers}
                    1
`;
