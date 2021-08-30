/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            creditBuy
        [Element/model]
            SnailmailErrorComponent
        [web.Element/tag]
            a
        [web.Element/class]
            btn
            btn-link
        [web.Element/href]
            {Env/snailmailCreditsUrl}
        [web.Element/target]
            _blank
`;
