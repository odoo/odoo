/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            avatar
        [Element/model]
            ThreadViewTopbarComponent
        [web.Element/tag]
            img
        [web.Element/class]
            ml-1
            mr-1
            rounded-circle
        [web.Element/src]
            @record
            .{ThreadViewTopbarComponent/avatarUrl}
        [web.Element/alt]
            {Locale/text}
                Avatar
        [web.Element/style]
            [web.scss/height]
                26
                px
            [web.scss/width]
                26
                px
            [web.scss/object-fit]
                cover
`;
