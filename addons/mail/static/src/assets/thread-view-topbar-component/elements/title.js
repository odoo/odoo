/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            title
        [Element/model]
            ThreadViewTopbarComponent
        [web.Element/class]
            d-flex
            flex-grow-1
            align-self-center
            align-items-center
        [web.Element/style]
            [web.scss/min-width]
                0
`;