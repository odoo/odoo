/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    :tmpId
        0
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            FileUploader/getAttachmentNextTemporaryId
        [Action/returns]
            Integer
        [Action/behavior]
            :tmpId
                @tmpId
                .{-}
                    1
            @tmpId
`;
