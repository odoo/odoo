/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Discuss/handleAddChannelAutocompleteSelect
        [Action/params]
            discuss
            ev
            ui
        [Action/behavior]
            {Discuss/clearIsAddingItem}
                @discuss
            {if}
                @ui
                .{Dict/get}
                    item
                .{Dict/get}
                    special
            .{then}
                :channel
                    {Record/doAsync}
                        [0]
                            @discuss
                        [1]
                            {Thread/performRpcCreateChannel}
                                [name]
                                    @discuss
                                    .{Discuss/addingChannelValue}
                                [privacy]
                                    @ui
                                    .{Dict/get}
                                        item
                                    .{Dict/get}
                                        special
                {Thread/open}
                    @channel
            .{else}
                :channel
                    {Record/insert}
                        [Record/models]
                            Thread
                        [Thread/id]
                            @ui
                            .{Dict/get}
                                item
                            .{Dict/get}
                                id
                        [Thread/model]
                            mail.channel
                {Thread/join}
                    @channel
                {Dev/comment}
                    Channel must be pinned immediately to be able to open
                    it before the result of join is received on the bus.
                {Record/update}
                    [0]
                        @channel
                    [1]
                        [Thread/isServerPinned]
                            true
                {Thread/open}
                    @channel
`;
