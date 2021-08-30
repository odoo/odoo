/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ThreadPreviewComponent
        [Model/fields]
            threadPreviewView
        {Dev/comment}
            The preview template is used by the discuss in mobile,
            and by the systray menu in order to show preview of threads.
        [Model/template]
            root
                sidebar
                    imageContainer
                        image
                        partnerImStatusIcon
                content
                    header
                        name
                        counter
                        callIndicator
                        headerAutogrowSeparator
                        date
                    core
                        inlineText
                            messageAuthorPrefix
                            inlineTextAfterPrefix
                        coreAutogrowSeparator
                        markAsRead
        [Model/actions]
            ThreadPreviewComponent/getImage
`;
