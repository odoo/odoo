import { Plugin } from "@html_editor/plugin";

export class DoubleClickImagePreviewPlugin extends Plugin {
    static id = "dblclickImagePreview";
    static dependencies = ["image"];

    setup() {
        this.addDomListener(this.editable, "dblclick", (e) => {
            if (e.target.tagName === "IMG") {
                this.dependencies.image.previewImage();
            }
        });
    }
}
