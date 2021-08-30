/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Chatter/_stopAttachmentsLoading
        [Action/params]
            chatter
        [Action/behavior]
            {web.Browser/clearTimeout}
                @chatter
                .{Chatter/attachmentsLoaderTimeout}
            {Record/update}
                [0]
                    @chatter
                [1]
                    [Chatter/attachmentsLoaderTimeout]
                        {Record/empty}
                    [Chatter/isShowingAttachmentsLoading]
                        false
`;
