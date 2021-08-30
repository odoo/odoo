/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Ref to the video element used for the video feedback.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            videoRef
        [Field/model]
            MediaPreview
        [Field/type]
            attr
        [Field/target]
            Element
        [Field/related]
            MediaPreview/mediaPreviewComponents
            Collection/first
            MediaPreviewComponent/videoDisplay
`;
