/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Contains the seen information for all members of the thread.
        FIXME This field should be readonly once task-2336946 is done.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            partnerSeenInfos
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            ThreadPartnerSeenInfo
        [Field/inverse]
            ThreadPartnerSeenInfo/thread
        [Field/isCausal]
            true
`;
