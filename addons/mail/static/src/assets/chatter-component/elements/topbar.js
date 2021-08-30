/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            topbar
        [Element/model]
            ChatterComponent
        [Field/target]
            ChatterTopbarComponent
        [ChatterTopbarComponent/chatter]
            @record
            .{ChatterComponent/chatter}
`;
