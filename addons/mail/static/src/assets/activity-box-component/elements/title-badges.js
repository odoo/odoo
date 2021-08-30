/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            titleBadges
        [Element/model]
            ActivityBoxComponent
        [web.Element/tag]
            span
        [web.Element/class]
            ms-2
        [Element/isPresent]
            @record
            .{ActivityBoxComponent/activityBoxView}
            .{ActivityBoxView/isActivityListVisible}
            .{isFalsy}
`;
