/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States if the user's camera is currently recording.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isVideoEnabled
        [Field/model]
            MediaPreview
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{MediaPreview/videoStream}
            .{!=}
                null
`;
