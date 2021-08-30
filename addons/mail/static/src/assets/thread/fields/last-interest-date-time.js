/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the date and time of the last interesting event that happened
        in this channel for this partner. This includes: creating, joining,
        pinning, and new message posted. It is contained as a Date object.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            lastInterestDateTime
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Date
`;
