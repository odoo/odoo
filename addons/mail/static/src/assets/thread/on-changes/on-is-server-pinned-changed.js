/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            onChange
        [onChange/name]
            onIsServerPinnedChanged
        [onChange/model]
            Thread
        [onChange/dependencies]
            Thread/isServerPinned
        [onChange/behavior]
            {Dev/comment}
                Handles change of pinned state coming from the server. Useful to
                clear pending state once server acknowledged the change.
                @see isPendingPinned
            {if}
                @record
                .{Thread/isServerPinned}
                .{=}
                    @record
                    .{Thread/isPendingPinned}
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [Thread/isPendingPinned]
                            {Record/empty}
`;
