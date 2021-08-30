/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            FileUploader/_createFormData
        [Action/params]
            composer
                [type]
                    Composer
            file
                [type]
                    web.File
            thread
                [type]
                    Thread
            record
                [type]
                    FileUploader
        [Action/returns]
            web.FormData
        [Action/behavior]
            :formData
                {Record/insert}
                    [Record/models]
                        web.FormData
            {web.FormData/append}
                [0]
                    @formData
                [1]
                    [csrf_token]
                        {Env/csrf_token}
                    [is_pending]
                        @composer
                        .{isTruthy}
                    [thread_id]
                        @thread
                        .{&}
                            @thread
                            .{Thread/id}
                    [thread_model]
                        @thread
                        .{&}
                            @thread
                            .{Thread/model}
                    [ufile]
                        [0]
                            @file
                        [1]
                            @file
                            .{web.File/name}
            @formData
`;
