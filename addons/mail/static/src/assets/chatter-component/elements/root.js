/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ChatterComponent
        [web.Element/style]
            [web.scss/position]
                relative
            [web.scss/display]
                flex
            [web.scss/flex]
                1
                1
                auto
            [web.scss/flex-direction]
                column
            [web.scss/width]
                {scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/background-color]
                {scss/$white}
            [web.scss/border-color]
                {scss/$border-color}
`;
