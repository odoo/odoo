/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            button
        [Element/model]
            MediaPreviewComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-lg
            p-0
            m-3
            rounded-circle
            fa
        [web.Element/style]
            [web.scss/height]
                4
                rem
            [web.scss/width]
                4
                rem
            [web.scss/font-size]
                1.5
                em
            [web.scss/line-height]
                4
                rem
`;
