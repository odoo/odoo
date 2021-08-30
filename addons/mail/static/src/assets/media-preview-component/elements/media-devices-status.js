/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mediaDevicesStatus
        [Element/model]
            MediaPreviewComponent
        [web.Element/tag]
            p
        [web.Element/class]
            text-light
        [web.Element/style]
            {scss/include}
                {scss/o-position-absolute}
                    [$bottom]
                        50%
`;
