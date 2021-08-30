/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            extension
        [Test/model]
            Attachment
        [Test/assertions]
            5
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            {Test/assert}
                @testEnv
                .{Record/findById}
                    [Attachment/id]
                        750
                .{isFalsy}

            :attachment
                @testEnv
                .{Record/insert}
                    [Record/models]
                        Attachment
                    [Attachment/filename]
                        test.txt
                    [Attachment/id]
                        750
                    [Attachment/mimetype]
                        text/plain
                    [Attachment/name]
                        test.txt
            {Test/assert}
                @attachment
            {Test/assert}
                @testEnv
                .{Record/findById}
                    [Attachment/id]
                        750
            {Test/assert}
                @attachment
                .{=}
                    @testEnv
                    .{Record/findById}
                        [Attachment/id]
                            750
            {Test/assert}
                @attachment
                .{Attachment/extension}
                .{=}
                    txt
`;
