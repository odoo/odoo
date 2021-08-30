/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            icon
        [Element/model]
            MessagingMenuComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-lg
            fa-comments
        [web.Element/role]
            img
        [web.Element/aria-label]
            {Locale/text}
                Messages
`;
