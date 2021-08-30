/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ThreadPartnerSeenInfo
        [Model/fields]
            lastFetchedMessage
            lastSeenMessage
            partner
            thread
        [Model/id]
            ThreadPartnerSeenInfos/thread
            .{&}
                ThreadPartnerSeenInfos/partner
`;
