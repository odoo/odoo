import { FileModel } from "@web/core/file_viewer/file_model";

export class StateFileModel extends FileModel {
    constructor(state) {
        super();
        this.state = state;
        for (const property of [
            "access_token",
            "checksum",
            "extension",
            "filename",
            "id",
            "mimetype",
            "name",
            "type",
            "tmpUrl",
            "url",
            "uploading",
        ]) {
            Object.defineProperty(this, property, {
                get() {
                    return this.state.fileData[property];
                },
                set(value) {
                    this.state.fileData[property] = value;
                },
                configurable: true,
                enumerable: true,
            });
        }
    }

    /**
     * For embedded files stored without an `id` (i.e. demo data or old
     * knowledge embedded files converted from "Knowledge Behavior"), allow
     * direct usage of the file `url` as an `urlRoute` for the fileViewer and
     * download attempts.
     *
     * @override
     */
    get urlRoute() {
        if (this.isUrl && !this.id) {
            return this.url;
        }
        return super.urlRoute;
    }
}
