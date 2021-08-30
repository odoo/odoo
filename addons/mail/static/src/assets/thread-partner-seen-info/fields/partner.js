/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Partner that this seen info is related to.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            partner
        [Field/model]
            ThreadPartnerSeenInfo
        [Field/type]
            one
        [Field/target]
            Partner
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
`;
