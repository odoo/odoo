/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the top bar of this thread view, if any.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            topbar
        [Field/model]
            ThreadView
        [Field/type]
            one
        [Field/target]
            ThreadViewTopbar
        [Field/inverse]
            ThreadViewTopbar/threadView
        [Field/isReadonly]
            true
        [Field/isCausal]
            true
        [Field/compute]
            {if}
                @record
                .{ThreadView/hasTopbar}
            .{then}
                {Record/insert}
                    [Record/models]
                        ThreadViewTopbar
            .{else}
                {Record/empty}
`;
