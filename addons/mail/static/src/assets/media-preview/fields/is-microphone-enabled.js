/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States if the user's microphone is currently recording.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isMicrophoneEnabled
        [Field/model]
            MediaPreview
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{MediaPreview/audioStream}
            .{!=}
                null
`;
