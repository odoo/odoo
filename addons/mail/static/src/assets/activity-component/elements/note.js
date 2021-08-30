/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            note
        [Element/model]
            ActivityComponent
        [Element/isPresent]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/note}
        [web.Element/htmlContent]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/noteAsMarkup}
        [web.Element/style]
            {scss/selector}
                [0]
                    p
                [1]
                    [web.scss/margin-bottom]
                        {scss/map-get}
                            {scss/$spacers}
                            0
`;
