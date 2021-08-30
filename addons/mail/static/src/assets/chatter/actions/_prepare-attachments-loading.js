/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Chatter/_prepareAttachmentsLoading
        [Action/params]
            chatter
        [Action/behavior]
            {Record/update}
                [0]
                    @chatter
                [1]
                    [Chatter/attachmentsLoaderTimeout]
                        {web.Browser/setTimeout}
                            [0]
                                {Chatter/_onAttachmentsLoadingTimeout}
                                    @record
                            [1]
                                {Env/loadingBaseDelayDuration}
`;
