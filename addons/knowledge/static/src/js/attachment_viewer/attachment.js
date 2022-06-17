/** @odoo-module */

export class Attachment {
    constructor(title, href, mimetype) {
        this.title = title;
        this.href = href;
        this.mimetype = mimetype;
        //this.complete -> probably something in owl, to investigate if not working
    }
    get isImage() {
        return [
            'image/bmp',
            'image/gif',
            'image/jpeg',
            'image/png',
            'image/svg+xml',
            'image/tiff',
            'image/x-icon',
        ].includes(this.mimetype);
    }
    get isPdf() {
        return this.mimetype === 'application/pdf';
    }
    get isText() {
        return [
            'application/javascript',
            'application/json',
            'text/css',
            'text/html',
            'text/plain',
        ].includes(this.mimetype);
    }
    get isVideo() {
        return [
            'audio/mpeg',
            'video/x-matroska',
            'video/mp4',
            'video/webm',
        ].includes(this.mimetype);
    }
}
