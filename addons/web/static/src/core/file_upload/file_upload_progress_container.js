import { Component, t, useProps } from "@odoo/owl";

export class FileUploadProgressContainer extends Component {
    static template = "web.FileUploadProgressContainer";
    props = useProps({
        Component: t.any(),
        shouldDisplay: t.function().optional(),
        fileUploads: t.object(),
    });
}
