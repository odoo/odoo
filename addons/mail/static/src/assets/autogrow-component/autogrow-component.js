/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            AutogrowComponent
        [web.Element/style]
            [web.scss/flex]
                1
                1
                auto
`;
