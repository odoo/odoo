/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            enableMicrophoneButton
        [Element/model]
            MediaPreviewComponent
        [Record/models]
            MediaPreviewComponent/button
        [web.Element/class]
            btn-danger
            fa-microphone-slash
        [Element/isPresent]
            @record
            .{MediaPreviewComponent/mediaPreview}
            .{MediaPreview/isMicrophoneEnabled}
            .{isFalsy}
        [Element/onClick]
            {MediaPreview/onClickEnableMicrophoneButton}
                [0]
                    @record
                    .{MediaPreviewComponent/mediaPreview}
                [1]
                    @ev
`;
