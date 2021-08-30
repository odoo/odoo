/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            layoutMenu
        [Field/model]
            RtcLayoutMenuComponent
        [Field/type]
            one
        [Field/target]
            RtcLayoutMenu
        [Field/isRequired]
            true
        [Field/inverse]
            RtcLayoutMenu/component
`;
