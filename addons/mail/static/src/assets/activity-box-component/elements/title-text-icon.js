/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            titleTextIcon
        [Element/model]
            ActivityBoxComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-fw
            {if}
                @record
                .{ActivityBoxComponent/activityBoxView}
                .{ActivityBoxView/isActivityListVisible}
            .{then}
                fa-caret-down
            {if}
                @record
                .{ActivityBoxComponent/activityBoxView}
                .{ActivityBoxView/isActivityListVisible}
                .{isFalsy}
            .{then}
                fa-caret-right
`;
