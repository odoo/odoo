/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ThreadIconComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/width]
                13px
            [web.scss/justify-content]
                center
            [web.scss/flex]
                0
                0
                auto
`;
