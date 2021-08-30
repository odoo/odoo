/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            typing
        [Element/model]
            ThreadIconComponent
        [web.Element/style]
            [web.scss/flex]
                1
                1
                auto
`;
