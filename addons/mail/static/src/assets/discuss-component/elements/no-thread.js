/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            noThread
        [Element/model]
            DiscussComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex]
                1
                1
                auto
            [web.scss/width]
                {scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/align-items]
                center
            [web.scss/justify-content]
                center
`;
