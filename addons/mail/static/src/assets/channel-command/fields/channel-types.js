/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines on which channel types 'this' is available.
        Type of the channel (e.g. 'chat', 'channel' or 'groups')
        This field should contain an array when filtering is desired.
        Otherwise, it should be undefined when all types are allowed.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            channelTypes
        [Field/model]
            ChannelCommand
        [Field/type]
            attr
`;
