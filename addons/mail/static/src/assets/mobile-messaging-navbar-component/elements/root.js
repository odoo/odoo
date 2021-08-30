/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            MobileMessagingNavbarComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex]
                0
                0
                auto
            [web.scss/z-index]
                1
            [web.scss/background-color]
                {scss/$white}
            [web.scss/box-shadow]
                0
                0
                8px
                {scss/gray}
                    400
`;
