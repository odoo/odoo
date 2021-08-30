/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            history
        [Element/model]
            VisitorBannerComponent
        [web.Element/style]
            [web.scss/margin-top]
                {scss/map-get}
                    {scss/$spacers}
                    1
`;
