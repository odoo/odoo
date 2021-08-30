/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            asideItem
        [Element/model]
            AttachmentCardComponent
        [web.Element/class]
            d-flex
            justify-content-center
            align-items-center
        [web.Element/style]
            [web.scss/width]
                100%
            [web.scss/height]
                100%
`;
