/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            threadView
        [Element/model]
            DiscussPublicViewComponent
        [Element/isPresent]
            @record
            .{DiscussPublicViewComponent/discussPublicView}
            .{DiscussPublicView/threadView}
        [Field/target]
            ThreadViewComponent
        [ThreadViewComponent/hasComposerThreadTyping]
            true
        [ThreadViewComponent/threadView]
            @record
            .{DiscussPublicViewComponent/discussPublicView}
            .{DiscussPublicView/threadView}
`;
