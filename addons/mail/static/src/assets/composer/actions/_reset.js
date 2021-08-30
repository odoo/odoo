/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Composer/_reset
        [Action/params]
            composer
        [Action/behavior]
            {Record/update}
                [0]
                    @composer
                [1]
                    [Composer/attachments]
                        {Record/empty}
                    [Composer/isLastStateChangeProgrammatic]
                        true
                    [Composer/mentionedChannels]
                        {Record/empty}
                    [Composer/mentionedPartners]
                        {Record/empty}
                    [Composer/textInputContent]
                        {Record/empty}
                    [Composer/textInputCursorEnd]
                        {Record/empty}
                    [Composer/textInputCursorStart]
                        {Record/empty}
                    [Composer/textInputSelectionDirection]
                        {Record/empty}
`;
