/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            uploadButton
        [Element/model]
            ActivityComponent
        [web.Element/tag]
            button
        [Record/models]
            ActivityComponent/toolButton
        [web.Element/class]
            btn
            btn-link
            btn-primary
            pt-0
            pl-0
        [Element/isPresent]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/fileUploader}
        [Element/onClick]
            {ActivityView/onClickUploadDocument}
                [0]
                    @record
                    .{ActivityComponent/activityView}
                [1]
                    @ev
`;
