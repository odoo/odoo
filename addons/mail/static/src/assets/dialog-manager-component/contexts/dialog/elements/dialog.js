/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            dialog
        [Element/model]
            DialogManagerComponent:dialog
        [Field/target]
            DialogComponent
        [DialogComponent/dialog]
            @record
            .{DialogManagerComponent:dialog/dialog}
`;
