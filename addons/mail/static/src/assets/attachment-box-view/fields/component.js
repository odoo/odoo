/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the OWL component displaying this attachment box.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            component
        [Field/model]
            AttachmentBoxView
        [Field/type]
            attr
        [Field/target]
            AttachmentBoxComponent
`;
