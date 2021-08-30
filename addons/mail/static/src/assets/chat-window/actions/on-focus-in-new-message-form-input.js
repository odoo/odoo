/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/onFocusInNewMessageFormInput
        [Action/params]
            record
                [type]
                    ChatWindow
            ev
                [type]
                    FocusEvent
        [Action/behavior]
            {if}
                {Record/exists}
                    @record
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [ChatWindow/isFocused]
                            true
`;
