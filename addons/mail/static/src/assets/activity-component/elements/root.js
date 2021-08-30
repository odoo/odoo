/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ActivityComponent
        [Element/onClick]
            {ActivityView/onClickActivity}
                [0]
                    @record
                    .{ActivityComponent/activityView}
                [1]
                    @ev
        [web.Element/class]
            d-flex
            p-2
`;
