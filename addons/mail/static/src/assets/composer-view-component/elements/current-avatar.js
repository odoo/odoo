/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            currentAvatar
        [Element/model]
            ComposerViewComponent
        [web.Element/tag]
            img
        [web.Element/class]
            rounded-circle
        [web.Element/style]
            [web.scss/width]
                36
                px
            [web.scss/height]
                36
                px
            [web.scss/object-fit]
                cover
`;
