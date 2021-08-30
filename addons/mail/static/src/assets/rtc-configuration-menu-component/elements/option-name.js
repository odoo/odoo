/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            optionName
        [Element/model]
            RtcConfigurationMenuComponent
        [Model/tag]
            span
        [web.Element/style]
            {web.scss/include}
                {web.scss/text-truncate}
            [web.scss/margin-inline-end]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/font-weight]
                bold
`;
