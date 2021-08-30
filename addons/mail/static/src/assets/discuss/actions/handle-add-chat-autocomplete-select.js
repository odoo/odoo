/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Discuss/handleAddChatAutocompleteSelect
        [Action/params]
            discuss
                [type]
                    Discuss
            ev
            ui
        [Action/behavior]
            {Env/openChat}
                [partnerId]
                    @ui
                    .{Dict/get}
                        item
                    .{Dict/get}
                        id
            {Discuss/clearIsAddingItem}
                @discuss
`;
