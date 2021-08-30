/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            loadingMoreIcon
        [Element/model]
            MessageListComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-spin
            fa-circle-o-notch
        [web.Element/style]
            [web.scss/margin-right]
                {scss/map-get}
                    {scss/$spacers}
                    1
`;
