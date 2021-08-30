/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            option
        [Element/model]
            RtcConfigurationMenuComponent
        [web.Element/style]
            [web.scss/min-height]
                40
                px
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    1
            [web.scss/margin]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            [web.scss/flex-wrap]
                wrap
`;
