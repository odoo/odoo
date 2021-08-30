/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            detailsAssignationUserAvatar
        [Element/model]
            ActivityComponent
        [web.Element/class]
            me-1
            rounded-circle
            align-text-bottom
        [web.Element/style]
            [web.scss/object-fit]
                cover
            [web.scss/height]
                18
                px
            [web.scss/width]
                18
                px
`;
