/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            EmojiListComponent/close
        [Action/params]
            record
        [Action/behavior]
            {Component/trigger}
                [0]
                    @record
                [1]
                    o-popover-close
`;
