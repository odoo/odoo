/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            loadingIcon
        [Element/model]
            ThreadViewComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-circle-o-notch
            fa-spin
        [web.Element/title]
            {Locale/text}
                Loading...
        [web.Element/role]
            img
        [web.Element/style]
            [web.scss/margin-right]
                {scss/map-get}
                    {scss/$spacers}
                    1
`;
