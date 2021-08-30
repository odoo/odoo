/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            VisitorBannerComponent
        [web.Element/style]
            [web.scss/border-bottom-width]
                {scss/$border-width}
            [web.scss/border-bottom-style]
                solid
            [web.scss/display]
                flex
            [web.scss/flex]
                0
                0
                auto
            [web.scss/padding]
                [0]
                    {scss/map-get}
                        {scss/$spacers}
                        4
                [1]
                    {scss/map-get}
                        {scss/$spacers}
                        2
            [web.scss/background]
                {scss/$white}
            [web.scss/border-bottom-color]
                {scss/gray}
                    400
`;
