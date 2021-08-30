/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            thread
        [Element/model]
            DiscussComponent
        [web.Element/style]
            [web.scss/flex]
                1
                1
                0
            [web.scss/min-width]
                0
`;
