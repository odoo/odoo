/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            onChange
        [onChange/name]
            onServerFoldStateChanged
        [onChange/model]
            Thread
        [onChange/dependencies]
            Thread/serverFoldState
        [onChange/behabior]
            {Dev/comment}
                Handles change of fold state coming from the server. Useful to
                synchronize corresponding chat window.
            {if}
                {Device/isMobile}
            .{then}
                {break}
            {if}
                @record
                .{Thread/serverFoldState}
                .{=}
                    closed
            .{then}
                {ChatWindowManager/closeThread}
                    @record
                    [notifyServer]
                        false
            .{else}
                {ChatWindowManager/openThread}
                    @record
                    [isFolded]
                        @record
                        .{Thread/serverFoldState}
                        .{=}
                            folded
                    [notifyServer]
                        false
`;
