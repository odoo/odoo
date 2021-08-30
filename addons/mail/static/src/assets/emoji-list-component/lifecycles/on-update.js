/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onUpdate
        [Lifecycle/model]
            EmojiListComponent
        [Lifecycle/behavior]
            {Component/trigger}
                @record
                o-popover-compute
`;
