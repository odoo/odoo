/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Fetch attachments linked to a record. Useful for populating the store
        with these attachments, which are used by attachment box in the chatter.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/fetchAttachments
        [Action/params]
            thread
                [type]
                    Thread
        [Action/behavior]
            :attachmentsData
                {Record/doAsync}
                    [0]
                        @thread
                    [1]
                        @env
                        .{Env/owlEnv}
                        .{Dict/get}
                            services
                        .{Dict/get}
                            rpc
                        .{Function/call}
                            [0]
                                [model]
                                    ir.attachment
                                [method]
                                    search_read
                                [domain]
                                    res_id
                                    .{=}
                                        @thread
                                        .{Thread/id}
                                    .{&}
                                        res_model
                                        .{=}
                                            @thread
                                            .{Thread/model}
                                [fields]
                                    id
                                    name
                                    mimetype
                                [orderBy]
                                    [0]
                                        [name]
                                            id
                                        [asc]
                                            false
                            [1]
                                [shadow]
                                    true
            {Record/update}
                [0]
                    @thread
                [1]
                    [Thread/originThreadAttachments]
                        @attachmentsData
            {Record/update}
                [0]
                    @thread
                [1]
                    [Thread/areAttachmentsLoaded]
                        true
`;
