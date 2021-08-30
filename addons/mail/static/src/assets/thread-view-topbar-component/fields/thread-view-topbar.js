/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadViewTopbar
        [Field/model]
            ThreadViewTopbarComponent
        [Field/type]
            one
        [Field/target]
            ThreadViewTopbar
        [Field/inverse]
            ThreadViewTopbarComponent/threadViewTopbarComponents
`;
