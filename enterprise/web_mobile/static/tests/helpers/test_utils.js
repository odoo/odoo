/** @odoo-module **/

    /**
     * Transforms base64 encoded data to a Blob object
     *
     * @param {string} b64Data
     * @param {string} contentType
     * @param {int} sliceSize
     * @returns {Blob}
     */
    function base64ToBlob(b64Data, contentType, sliceSize) {
        contentType = contentType || '';
        sliceSize = sliceSize || 512;

        const byteCharacters = atob(b64Data);
        let byteArrays = [];

        for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
            const slice = byteCharacters.slice(offset, offset + sliceSize);
            const byteNumbers = Array.from(slice).map((char) => char.charCodeAt(0));
            byteArrays.push(new Uint8Array(byteNumbers));
        }

        return new Blob(byteArrays, { type: contentType });
    }

    export default {
        base64ToBlob,
    };
