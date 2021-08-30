/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mediaDevicesStatusCameraOff
        [Element/model]
            MediaPreviewComponent
        [Record/models]
            MediaPreviewComponent/mediaDevicesStatus
        [Element/isPresent]
            @record
            .{MediaPreviewComponent/mediaPreview}
            .{MediaPreview/doesBrowserSupportMediaDevices}
            .{&}
                @record
                .{MediaPreviewComponent/mediaPreview}
                .{MediaPreview/isVideoEnabled}
                .{isFalsy}
        [web.Element/textContent]
            {Locale/text}
                Camera is off
        [web.Element/class]
            position-absolute
`;
