/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            separator
        [Element/model]
            ThreadTypingIconComponent
        [web.Element/style]
            [web.scss/min-width]
                1px
            [web.scss/flex]
                1
                0
                auto
`;
