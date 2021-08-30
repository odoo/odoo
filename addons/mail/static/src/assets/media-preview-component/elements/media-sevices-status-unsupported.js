/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mediaDevicesStatusUnsupported
        [Element/model]
            MediaPreviewComponent
        [Record/models]
            MediaPreviewComponent/mediaDevicesStatus
        [Element/isPresent]
            @record
            .{MediaPreviewComponent/mediaPreview}
            .{MediaPreview/doesBrowserSupportMediaDevices}
            .{isFalsy}
        [web.Element/textContent]
            {Locale/text}
                Your browser does not support videoconference
`;
