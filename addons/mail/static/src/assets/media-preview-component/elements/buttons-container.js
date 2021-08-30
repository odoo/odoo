/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonsContainer
        [Element/model]
            MediaPreviewComponent
        [web.Element/style]
            {scss/include}
                {scss/o-position-absolute}
                    [$bottom]
                        0
`;
