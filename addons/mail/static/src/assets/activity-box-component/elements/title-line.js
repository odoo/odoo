/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            titleLine
        [Element/model]
            ActivityBoxComponent
        [web.Element/tag]
            hr
        [web.Element/class]
            w-auto
            flex-grow-1
        [web.Element/style]
            [web.scss/border-top]
                {scss/$border-width}
                {scss/$border-color}
                dashed
`;
