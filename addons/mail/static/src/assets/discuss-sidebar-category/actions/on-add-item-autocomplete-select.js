/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussSidebarCategory/onAddItemAutocompleteSelect
        [Action/params]
            ev
                [type]
                    jQuery.Event
            ui
                [type]
                    Object
                [description]
                    @param {Object} ui.item
                    @param {integer} ui.item.id
            record
                [type]
                    DiscussSidebarCategory
        [Action/behavior]
            {switch}
                @record
                .{DiscussSidebarCategory/autocompleteMethod}
            .{case}
                [channel]
                    {Discuss/handleAddChannelAutocompleteSelect}
                        @ev
                        @ui
                [chat]
                    {Discuss/handleAddChatAutocompleteSelect}
                        @ev
                        @ui
`;
