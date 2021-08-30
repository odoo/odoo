/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            fileUploader
        [Field/model]
            ActivityView
        [Field/type]
            one
        [Field/target]
            FileUploader
        [Field/isCausal]
            true
        [Field/inverse]
            FileUploader/activityView
        [Field/compute]
            {if}
                @record
                .{ActivityView/activity}
                .{Activity/category}
                .{=}
                    upload_file
            .{then}
                {Record/insert}
                    [Record/models]
                        FileUploader
            .{else}
                {Record/empty}
`;
