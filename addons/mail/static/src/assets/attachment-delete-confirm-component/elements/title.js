/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            title
        [Element/model]
            AttachmentDeleteConfirmComponent
        [web.Element/tag]
            h4
        [web.Element/class]
            m-3
        [web.Element/textContent]
            {Locale/text}
                Confirmation
`;
