/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Send the attachment for the browser to download.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Attachment/download
        [Action/params]
            record
                [type]
                    Attachment
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                navigate
            .{Function/call}
                [0]
                    /web/content/ir.attachment/
                    .{+}
                        @record
                        .{Attachment/id}
                    .{+}
                        /datas
                [1]
                    [download]
                        true
`;
