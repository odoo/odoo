/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            descriptionTypeLabel
        [Element/model]
            ActivityComponent
        [web.Element/class]
            d-md-table-cell
            font-weight-bold
            text-md-right
            m-0
            py-md-1
            px-md-4
        [web.Element/textContent]
            {Locale/text}
                Activity type
`;
