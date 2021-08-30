/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            enableVideoButton
        [Element/model]
            MediaPreviewComponent
        [Record/models]
            MediaPreviewComponent/button
        [web.Element/class]
            btn-danger
            fa-eye-slash
        [Element/isPresent]
            @record
            .{MediaPreviewComponent/mediaPreview}
            .{MediaPreview/isVideoEnabled}
            .{isFalsy}
        [Element/onClick]
            {MediaPreview/onClickEnableVideoButton}
                [0]
                    @record
                    .{MediaPreviewComponent/mediaPreview}
                [1]
                    @ev
`;
