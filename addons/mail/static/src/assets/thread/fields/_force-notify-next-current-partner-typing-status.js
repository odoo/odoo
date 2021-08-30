/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether the next request to notify current partner
        typing status should always result to making RPC, regardless of
        whether last notified current partner typing status is the same.
        Most of the time we do not want to notify if value hasn't
        changed, exception being the long typing scenario of current
        partner.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _forceNotifyNextCurrentPartnerTypingStatus
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
