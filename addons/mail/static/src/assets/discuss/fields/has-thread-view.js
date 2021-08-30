/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether 'this.thread' should be displayed.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasThreadView
        [Field/model]
            Discuss
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {if}
                @record
                .{Discuss/thread}
                .{isFalsy}
                .{|}
                    @record
                    .{Discuss/discussView}
                    .{isFalsy}
            .{then}
                false
            .{elif}
                {Device/isMobile}
                .{&}
                    @record
                    .{Discuss/activeMobileNavbarTabId}
                    .{!=}
                        mailbox
                    .{|}
                        @record
                        .{Discuss/thread}
                        .{Thread/model}
                        .{!=}
                            mail.box
            .{then}
                false
            .{else}
                true
`;
