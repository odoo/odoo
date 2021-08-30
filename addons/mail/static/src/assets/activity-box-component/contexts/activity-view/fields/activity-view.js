/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            activityView
        [Field/model]
            ActivityBoxComponent:activityView
        [Field/type]
            one
        [Field/target]
            ActivityView
        [Field/isRequired]
            true
`;
