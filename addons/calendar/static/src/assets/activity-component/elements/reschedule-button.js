/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
            ActivityComponent/toolButton
        [Element/name]
            rescheduleButton
        [Element/model]
            ActivityComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-link
        [web.Element/onClick]
            {ActivityView/onClickEdit}
                [0]
                    @record
                    .{ActivityComponent/activityView}
                [1]
                    @ev
`;
