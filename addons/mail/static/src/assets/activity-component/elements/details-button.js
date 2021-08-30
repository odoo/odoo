/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            detailsButton
        [Element/model]
            ActivityComponent
        [web.Element/tag]
            a
        [Record/models]
            Hoverable
        [web.Element/class]
            btn
            py-0
            {if}
                @record
                .{ActivityComponent/activityView}
                .{ActivityView/areDetailsVisible}
            .{then}
                text-primary
            .{else}
                btn-link
                btn-primary
        [Element/onClick]
            {ActivityView/onClickDetailsButton}
                [0]
                    @record
                    .{ActivityComponent/activityView}
                [1]
                    @ev
        [web.Element/role]
            button
        [web.Element/style]
            {web.scss/o-hover-text-color}
                [web.scss/$default-color]
                    {web.scss/$o-main-color-muted}
`;
