/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            value
        [Field/model]
            MessageViewComponent:trackingValueContainer
        [Field/type]
            one
        [Field/target]
            TrackingValue
        [Field/isRequired]
            true
`;
