/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            sidebar
        [Element/model]
            VisitorBannerComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex]
                0
                0
                {scss/$o-mail-message-sidebar-width}
            [web.scss/justify-content]
                center
            [web.scss/margin-inline-end]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/max-width]
                {scss/$o-mail-message-sidebar-width}
`;
