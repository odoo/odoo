/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Performs the 'channel_get' RPC on 'mail.channel'.

        'openChat' is preferable in business code because it will avoid the
        RPC if the chat already exists.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/performRpcCreateChat
        [Action/params]
            partnerIds
                [type]
                    Collection<Integer>
            pinForCurrentPartner
                [type]
                    Boolean
        [Action/returns]
            Thread
                the created or existing chat
        [Action/behavior]
            {Dev/comment}
                TODO FIX: potential duplicate chat task-2276490
            :data
                @env
                .{Env/owlEnv}
                .{Dict/get}
                    services
                .{Dict/get}
                    rpc
                .{Function/call}
                    [model]
                        mail.channel
                    [method]
                        channel_get
                    [kwargs]
                        [context]
                            {Record/insert}
                                [Record/models]
                                    Object
                                @env
                                .{Env/owlEnv}
                                .{Dict/get}
                                    session
                                .{Dict/get}
                                    user_content
                            {Dev/comment}
                                optimize the return value by avoiding
                                useless queries in non-mobile devices
                            [isMobile]
                                {Device/isMobile}
                        [partners_to]
                            @partnerIds
                        [pin]
                            @pinForCurrentPartner
            {if}
                @data
                .{isFalsy}
            .{then}
                {break}
            {Record/insert}
                [Record/models]
                    Thread
                {Thread/convertData}
                    @data
`;
