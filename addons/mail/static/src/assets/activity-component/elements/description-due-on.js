/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            descriptionDueOn
        [Element/model]
            ActivityComponent
        [web.Element/class]
            d-md-table-row
`;
