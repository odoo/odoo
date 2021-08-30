/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MailTemplateComponent
        [Model/fields]
            activity
            mailTemplate
        [Model/template]
            root
                {Dev/comment}
                    TODO: improve format for proper locale
                icon
                name
                colon
                preview
                text
                send
`;
