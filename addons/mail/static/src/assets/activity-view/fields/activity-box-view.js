/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            activityBoxView
        [Field/model]
            ActivityView
        [Field/type]
            one
        [Field/target]
            ActivityBoxView
        [Field/isRequired]
            true
        [Field/isReadonly]
            true
        [Field/inverse]
            ActivityBoxView/activityViews
`;
