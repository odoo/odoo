/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            title
        [Element/model]
            ActivityBoxComponent
        [web.Element/tag]
            a
        [web.Element/class]
            btn
            d-flex
            align-items-center
            mt-4
            p-0
            w-100
            font-weight-bold
        [web.Element/role]
            button
        [Element/isPresent]
            @record
            .{ActivityBoxComponent/activityBoxView}
            .{ActivityBoxView/chatter}
            .{Chatter/thread}
        [Element/onClick]
            {Record/update}
                [0]
                    @record
                    .{ActivityBoxComponent/activityBoxView}
                [1]
                    [ActivityBoxView/isActivityListVisible]
                        @record
                        .{ActivityBoxComponent/hactivityBoxView}
                        .{ActivityBoxView/isActivityListVisible}
`;
