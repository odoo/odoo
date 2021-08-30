/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            videoDisplay
        [Element/model]
            MediaPreviewComponent
        [web.Element/tag]
            video
        [web.Element/class]
            shadow
            rounded
            bg-dark
        [web.Element/height]
            480
        [web.Element/width]
            640
`;
