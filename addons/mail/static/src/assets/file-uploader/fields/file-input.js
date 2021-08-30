/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            fileInput
        [Field/model]
            FileUploader
        [Field/type]
            attr
        [Field/target]
            web.Element
        [Field/compute]
            {Dev/comment}
                Create an HTML element that will serve as file input.
                This element does not need to be inserted in the DOM since it's just
                use to trigger the file browser and start the upload process.
            :fileInput
                {Record/insert}
                    [Record/models]
                        web.Element
                    [web.Element/tag]
                        input
            {Record/update}
                [0]
                    @fileInput
                [1]
                    [web.Element/type]
                        file
                    [web.Element/multiple]
                        true
                    [web.Element/onchange]
                        {FileUploader/onChangeAttachment}
                            @record
            @fileInput
`;
