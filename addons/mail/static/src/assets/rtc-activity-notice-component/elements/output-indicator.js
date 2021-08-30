/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            outputIndicator
        [Element/model]
            RtcActivityNoticeComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-lg
            {if}
                {Rtc/sendDisplay}
                .{isFalsy}
                .{&}
                    {Rtc/sendUserVideo}
                    .{isFalsy}
            .{then}
                fa-microphone
            {if}
                {Rtc/sendUserVideo}
            .{then}
                fa-video-camera
            {if}
                {Rtc/sendDisplay}
            .{then}
                fa-desktop
        [web.Element/style]
            [web.scss/margin-inline-end]
                {scss/map-get}
                    {scss/$spacers}
                    2
`;
