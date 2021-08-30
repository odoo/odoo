/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the thread viewer linked to this discuss public view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadViewer
        [Field/model]
            DiscussPublicView
        [Field/type]
            one
        [Field/target]
            ThreadViewer
        [Field/isCausal]
            true
        [Field/inverse]
            ThreadViewer/discussPublicView
`;
