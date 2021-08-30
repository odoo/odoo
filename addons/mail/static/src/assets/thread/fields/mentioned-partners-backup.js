/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the last mentioned partners of the last composer related
        to this thread. Useful to sync the composer when re-creating it.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            mentionedPartnersBackup
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Partner
`;
