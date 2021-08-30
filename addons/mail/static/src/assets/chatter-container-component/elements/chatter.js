/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            chatter
        [Element/model]
            ChatterContainerComponent
        [Field/target]
            ChatterComponent
        [ChatterComponent/chatter]
            @record
            .{ChatterContainerComponent/chatter}
`;
