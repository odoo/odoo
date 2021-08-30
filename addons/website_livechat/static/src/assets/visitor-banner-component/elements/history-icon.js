/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            historyIcon
        [Element/model]
            VisitorBannerComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-history
        [web.Element/aria-label]
            {Locale/text}
                History
        [web.Element/style]
            [web.scss/margin-inline-end]
                {scss/map-get}
                    {scss/$spacers}
                    1
`;
