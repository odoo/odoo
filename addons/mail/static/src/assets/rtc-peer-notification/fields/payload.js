/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            payload
        [Field/model]
            RtcPeerNotification
        [Field/isReadonly]
            true
`;
