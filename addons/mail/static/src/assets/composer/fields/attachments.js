/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States which attachments are currently being created in this composer.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachments
        [Field/model]
            Composer
        [Field/type]
            many
        [Field/target]
            Attachment
        [Field/inverse]
            Attachment/composer
`;
