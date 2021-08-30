/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            RtcConfigurationMenuComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/overflow-y]
                auto
            [web.scss/flex-direction]
                column
            [web.scss/margin-left]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/user-select]
                none
`;
