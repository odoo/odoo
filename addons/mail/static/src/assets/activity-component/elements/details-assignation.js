/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            detailsAssignation
        [Element/model]
            ActivityComponent
        [web.Element/class]
            d-md-table-cell
            py-md-1
            pr-4
`;
