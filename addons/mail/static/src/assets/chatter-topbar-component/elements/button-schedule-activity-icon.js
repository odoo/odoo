/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonScheduleActivityIcon
        [Element/model]
            ChatterTopbarComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-clock-o
`;
