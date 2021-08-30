/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            icon
        [Element/model]
            MessageSeenIndicatorComponent
        [web.Element/style]
            {Dev/comment}
                fa icons have a line height of 1 by default which breaks alignment
            [web.scss/line-height]
                1.5
`;
