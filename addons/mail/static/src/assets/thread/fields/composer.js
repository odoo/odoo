/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the composer state of this thread.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            composer
        [Field/model]
            Thread
        [Field/type]
            one
        [Field/target]
            Composer
        [Field/inverse]
            Composer/thread
        [Field/isCausal]
            true
        [Field/isReadonly]
            true
        [Field/compute]
            {if}
                @record
                .{Thread/model}
                .{=}
                    mail.box
            .{then}
                {Record/empty}
            .{else}
                {Record/insert}
                    [Record/models]
                        Composer
`;
