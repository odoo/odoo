/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonEmojisIcon
        [Element/model]
            ComposerViewComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-smile-o
`;
