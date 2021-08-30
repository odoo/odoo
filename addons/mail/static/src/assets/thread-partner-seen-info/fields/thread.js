/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Thread (channel) that this seen info is related to.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            thread
        [Field/model]
            ThreadPartnerSeenInfo
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/inverse]
            Thread/partnerSeenInfos
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
`;
