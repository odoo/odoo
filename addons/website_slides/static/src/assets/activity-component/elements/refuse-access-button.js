/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            refuseAccessButton
        [Element/feature]
            website_slides
        [Element/model]
            ActivityComponent
        [web.Element/tag]
            button
        [Record/models]
            ActivityComponent/toolButton
        [web.Element/class]
            btn
            btn-link
        [Element/isPresent]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/requestingPartner}
            .{&}
                @record
                .{ActivityComponent/activityView}
                .{ActivityView/activity}
                .{Activity/thread}
                .{Thread/model}
                .{=}
                    slide.channel
        [Element/onClick]
            {ActivityView/onRefuseAccess}
                [0]
                    @record
                    .{ActivityComponent/activityView}
                [1]
                    @ev
`;
