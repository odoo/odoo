/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ComposerSuggestedRecipientListComponent
        [web.Element/style]
            [web.scss/margin-bottom]
                {scss/map-get}
                    {scss/$spacers}
                    2
`;
