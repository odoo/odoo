/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the last mentioned channels of the last composer related
        to this thread. Useful to sync the composer when re-creating it.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            mentionedChannelsBackup
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Thread
`;
