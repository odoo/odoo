/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ComposerTextInputComponent
        [web.Element/style]
            [web.scss/min-width]
                0
            [web.scss/position]
                relative
`;
