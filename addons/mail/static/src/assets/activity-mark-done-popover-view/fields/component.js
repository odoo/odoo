/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            component
        [Field/model]
            ActivityMarkDonePopoverView
        [Field/type]
            attr
        [Field/target]
            ActivityComponent
        [Field/inverse]
            ActivityComponent/activityView
`;
