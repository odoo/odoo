/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        List of partners that have been invited to the RTC call of this channel.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            invitedPartners
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Partner
`;
