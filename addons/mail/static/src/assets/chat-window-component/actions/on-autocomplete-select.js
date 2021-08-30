/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Called when selecting an item in the autocomplete input of the
        'new_message' chat window.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindowComponent/_onAutocompleteSelect
        [Action/params]
            ev
            record
            ui
        [Action/behavior]
            :chat
                {Env/getChat}
                    [partnerId]
                        @ui
                        .{Dict/get}
                            item
                        {Dict/get}
                            id
            {if}
                @chat
                .{isFalsy}
            .{then}
                {break}
            {ChatWindowManager/openThread}
                @chat
                [makeActive]
                    true
                [replaceNewMessage]
                    true
`;
