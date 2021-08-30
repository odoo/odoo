/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onUpdate
        [Lifecycle/model]
            DiscussComponent
        [Lifecycle/behavior]
            {Discuss/open}
            {if}
                {Discuss/thread}
            .{then}
                {Component/trigger}
                    @record
                    o-push-state-action-manager
            {DiscussComponent/_updateLocalStoreProps}
                @record
`;
