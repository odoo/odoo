/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether this thread should has the invite feature.
        Only makes sense for channels.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasInviteFeature
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{Thread/model}
            .{=}
                mail.channel
`;
