/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            MediaPreviewComponent
        [web.Element/class]
            position-relative
            d-flex
            justify-content-center
        [web.Element/style]
            [web.scss/max-width]
                max-content
`;
