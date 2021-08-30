/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            icon
        [Element/model]
            MailTemplateComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-envelope-o
        [web.Element/title]
            {Locale/text}
                Mail
        [web.Element/role]
            img
`;
