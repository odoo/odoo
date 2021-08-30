/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            separatorLine
        [Element/model]
            MessageListComponent
        [web.Element/style]
            [web.scss/flex]
                1
                1
                auto
            [web.scss/width]
                auto
            [web.scss/border-color]
                {scss/$border-color}
`;
