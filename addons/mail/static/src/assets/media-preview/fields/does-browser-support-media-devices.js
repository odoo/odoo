/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether the browser has the required APIs for
        microphone/camera recording.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            doesBrowserSupportMediaDevices
        [Field/model]
            MediaPreview
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {web.Browser/navigator}
            .{web.Navigator/mediaDevices}
            .{&}
                {web.Browser/navigator}
                .{web.Navigator/mediaDevices}
                .{web.MediaDevices/getUserMedia}
            .{&}
                {web.Browser/MediaStream}
`;
