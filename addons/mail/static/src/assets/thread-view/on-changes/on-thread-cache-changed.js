/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            onChange
        [onChange/name]
            onThreadCacheChanged
        [onChange/model]
            ThreadView
        [onChange/dependencies]
            ThreadView/threadCache
        [onChange/behavior]
            {Dev/comment}
                clear obsolete hints
            {Record/update}
                [0]
                    @record
                [1]
                    [ThreadView/componentHintList]
                        {Record/empty}
            {ThreadView/addComponentHint}
                @record
                change-of-thread-cache
            {if}
                @record
                .{ThreadView/threadCache}
            .{then}
                {Record/update}
                    [0]
                        @record
                        .{ThreadView/threadCache}
                    [1]
                        [ThreadCache/isCacheRefreshRequested]
                            true
                        [ThreadCache/isMarkAllAsReadRequested]
                            true
            {Record/update}
                [0]
                    @record
                [1]
                    [ThreadView/lastVisibleMessage]
                        {Record/empty}
`;
