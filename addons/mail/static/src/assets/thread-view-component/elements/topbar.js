/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            topbar
        [Element/model]
            ThreadViewComponent
        [Field/target]
            ThreadViewTopbarComponent
        [web.Element/class]
            border-bottom
        [ThreadViewTopbarComponent/threadViewTopbar]
            @record
            .{ThreadViewComponent/threadView}
            .{ThreadView/topbar}
        [Element/isPresent]
            @record
            .{ThreadViewComponent/threadView}
            .{ThreadView/topbar}
`;
