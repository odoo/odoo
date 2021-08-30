/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the 'Thread' that should be displayed by 'this'.

        Only pinned threads are allowed in discuss.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            thread
        [Field/model]
            Discuss
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/compute]
            {if}
                {Env/inbox}
                .{&}
                    {Device/isMobile}
                .{&}
                    @record
                    .{Discuss/activeMobileNavbarTabId}
                    .{=}
                        mailbox
                .{&}
                    @record
                    .{Discuss/initActiveId}
                    .{!=}
                        mail.box_inbox
                .{&}
                    @record
                    .{Discuss/thread}
                    .{isFalsy}
            .{then}
                {Dev/comment}
                    After loading Discuss from an arbitrary tab other then 'mailbox',
                    switching to 'mailbox' requires to also set its inner-tab ;
                    by default the 'inbox'.
                {Env/inbox}
            .{elif}
                @record
                .{Discuss/thread}
                .{isFalsy}
                .{|}
                    @record
                    .{Discuss/thread}
                    .{Thread/isPinned}
                    .{isFalsy}
            .{then}
                {Record/empty}
`;
