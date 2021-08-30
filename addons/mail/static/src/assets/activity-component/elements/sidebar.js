/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            sidebar
        [Element/model]
            ActivityComponent
        [web.Element/class]
            mr-3
        [web.Element/style]
            [web.scss/width]
                {web.scss/$o-mail-thread-avatar-size}
`;
