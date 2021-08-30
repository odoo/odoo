/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            alertLoadingFailedText
        [Element/model]
            MessageListComponent
        [web.Element/textContent]
            {Locale/text}
                An error occurred while fetching messages.
`;
