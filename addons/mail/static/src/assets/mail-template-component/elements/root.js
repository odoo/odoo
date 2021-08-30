/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            MailTemplateComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex]
                0
                0
                auto
            [web.scss/align-items]
                center
`;
