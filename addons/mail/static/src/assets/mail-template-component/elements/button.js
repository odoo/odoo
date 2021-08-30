/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            button
        [Element/model]
            MailTemplateComponent
        [web.Element/style]
            [web.scss/padding-top]
                {scss/map-get}
                    {scss/$spacers}
                    0
            [web.scss/padding-bottom]
                {scss/map-get}
                    {scss/$spacers}
                    0
`;
