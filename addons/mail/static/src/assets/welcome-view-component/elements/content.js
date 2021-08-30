/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            content
        [Element/model]
            WelcomeViewComponent
        [web.Element/class]
            d-flex
            justify-content-center
`;
