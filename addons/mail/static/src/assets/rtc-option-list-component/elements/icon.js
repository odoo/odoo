/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            icon
        [Element/model]
            RtcOptionListComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-lg
        [web.Element/style]
            [web.scss/margin]
                {scss/map-get}
                    {scss/$spacers}
                    1
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    1
`;
