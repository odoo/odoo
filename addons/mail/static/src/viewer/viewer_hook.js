/* @odoo-module */

import { onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Viewer } from "./viewer";

let id = 1;

export class Viewable {
    mimetype;
    url;
    name;

    constructor(name, url, mimetype) {
        this.name = name;
        this.url = url;
        this.mimetype = mimetype;
    }

    get isText() {
        const textMimeType = [
            "application/javascript",
            "application/json",
            "text/css",
            "text/html",
            "text/plain",
        ];
        return textMimeType.includes(this.mimetype);
    }

    get isPdf() {
        return this.mimetype === "application/pdf";
    }

    get isImage() {
        const imageMimetypes = [
            "image/bmp",
            "image/gif",
            "image/jpeg",
            "image/png",
            "image/svg+xml",
            "image/tiff",
            "image/x-icon",
        ];
        return imageMimetypes.includes(this.mimetype);
    }

    get isVideo() {
        const videoMimeTypes = ["audio/mpeg", "video/x-matroska", "video/mp4", "video/webm"];
        return videoMimeTypes.includes(this.mimetype);
    }

    get isUrlYoutube() {
        return !!this.url && this.url.includes("youtu");
    }

    get isViewable() {
        return this.isText || this.isImage || this.isVideo || this.isPdf || this.isUrlYoutube;
    }
}

export function useViewer() {
    const viewerId = `mail.viewer${id++}`;
    /**
     * @param {Viewable} viewable
     * @param {Viewable[]} viewables
     */
    function open(viewable, viewables = [viewable]) {
        if (!viewable.isViewable) {
            return;
        }
        if (viewables.length > 0) {
            const viewablesViewable = viewables.filter((viewable) => viewable.isViewable);
            const index = viewablesViewable.indexOf(viewable);
            registry.category("main_components").add(viewerId, {
                Component: Viewer,
                props: { viewables: viewablesViewable, startIndex: index, close },
            });
        }
    }

    function close() {
        registry.category("main_components").remove(viewerId);
    }
    onWillDestroy(close);
    return { open, close };
}
