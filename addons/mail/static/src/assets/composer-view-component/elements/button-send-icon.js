/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonSendIcon
        [Element/model]
            ComposerViewComponent
        [Element/isPresent]
            {Device/isMobile}
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-paper-plane-o
`;
