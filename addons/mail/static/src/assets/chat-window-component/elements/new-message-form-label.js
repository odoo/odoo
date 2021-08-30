/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            newMessageFormLabel
        [Element/model]
            ChatWindowComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            {Locale/text}
                To:
        [web.Element/style]
            [web.scss/margin-right]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/flex]
                0
                0
                auto
`;
