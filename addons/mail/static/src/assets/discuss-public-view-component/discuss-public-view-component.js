/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            DiscussPublicViewComponent
        [Model/fields]
            discussPublicView
        [Model/template]
            root
                threadView
                welcomeView
`;
