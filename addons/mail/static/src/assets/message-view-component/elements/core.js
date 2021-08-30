/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            core
        [Element/model]
            MessageViewComponent
        [web.Element/class]
            flex-grow-1
        [web.Element/style]
            [web.scss/min-width]
                0
                {Dev/comment}
                    allows this flex child to shrink more than its content
            [web.scss/margin-inline-end]
                {scss/map-get}
                    {scss/$spacers}
                    4
`;
