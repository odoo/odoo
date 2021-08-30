/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DialogManagerComponent/_checkDialogOpen
        [Action/behavior]
            {if}
                {DialogManager/dialogs}
                .{Collection/length}
                .{>}
                    0
            .{then}
                {Record/update}
                    [0]
                        {web.Browser/document}
                        .{web.Document/body}
                    [1]
                        [web.Element/class]
                            {Field/add}
                                modal-open
            .{else}
                {Record/update}
                    [0]
                        {web.Browser/document}
                        .{web.Document/body}
                    [1]
                        [web.Element/class]
                            {Field/remove}
                                modal-open
`;
