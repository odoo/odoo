/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            thread
        [Element/model]
            ChatterComponent
        [Field/target]
            ThreadViewComponent
        [Element/isPresent]
            @record
            .{ChatterComponent/chatter}
            .{Chatter/threadView}
        [ThreadViewComponent/getScrollableElement]
            {ChatterComponent/getScrollableElement}
                @record
        [ThreadViewComponent/hasScrollAdjust]
            @record
            .{ChatterComponent/chatter}
            .{Chatter/hasMessageListScrollAdjust}
        [ThreadViewComponent/threadView]
            @record
            .{ChatterComponent/chatter}
            .{Chatter/threadView}
`;
