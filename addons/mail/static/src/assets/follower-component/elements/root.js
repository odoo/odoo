/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            FollowerComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-flow]
                row
            [web.scss/justify-content]
                space-between
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    0
`;
