/* @odoo-module */

import { FileViewer as WebFileViewer } from "@web/core/file_viewer/file_viewer";

export class FileViewer extends WebFileViewer {

    static template = "mail.FileViewer";

    static props = [
        ...WebFileViewer.props,
        "onClickUnlink?"
    ]

    async onClickUnlink() {
        const deleted = await this.props.onClickUnlink(this.state.file);
        if (deleted) {
           this.close();
        }
    }

}
