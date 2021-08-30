/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            question
        [Element/model]
            DeleteMessageConfirmDialogComponent
        [web.Element/tag]
            p
        [web.Element/class]
            mx-3
            mb-3
        [web.Element/textContent]
            {Locale/text}
                Are you sure you want to delete this message?
`;
