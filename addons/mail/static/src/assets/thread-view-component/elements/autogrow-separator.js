/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            autogrowSeparator
        [Element/model]
            ThreadViewComponent
        [Record/models]
            AutogrowComponent
        [Element/isPresent]
            @record
            .{ThreadViewComponent/threadView}
            .{ThreadView/composerView}
`;
