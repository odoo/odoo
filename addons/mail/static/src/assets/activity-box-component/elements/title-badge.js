/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            titleBadge
        [Element/model]
            ActivityBoxComponent
        [web.Element/tag]
            span
        [web.Element/class]
            me-1
            badge
            border-0
            rounded-circle
`;
