/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Ref to the audio element used for the audio feedback.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            audioRef
        [Field/model]
            MediaPreview
        [Field/type]
            attr
        [Field/target]
            Element
        [Field/related]
            MediaPreview/mediaPreviewComponents
            Element/first
            MediaPreviewComponent/audioPlayer
`;
