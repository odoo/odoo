/** @odoo-module **/

/**
 * @typedef {import("@web/core/orm_service").ORM} ORM
 */

/**
 *
 * Upload files on the server and link the files to a record as attachment.
 *
 * Implements the `FileStore` interface defined by o-spreadsheet.
 * https://github.com/odoo/o-spreadsheet/blob/300da461b23b5f3db017270192893d4a972bacf0/src/types/files.ts#L4
 *
 */
export class RecordFileStore {
    /**
     *
     * @param {string} resModel
     * @param {number} resId
     * @param {*} http
     * @param {ORM} orm
     */
    constructor(resModel, resId, http, orm) {
        this.resModel = resModel;
        this.resId = resId;
        this.http = http;
        this.orm = orm;
    }

    /**
     * Upload a file on the server and returns the path to the file.
     */
    async upload(file) {
        const route = "/web/binary/upload_attachment";
        const params = {
            ufile: [file],
            csrf_token: odoo.csrf_token,
            model: this.resModel,
            id: this.resId,
        };
        const fileData = JSON.parse(await this.http.post(route, params, "text"))[0];
        const [accessToken] = await this.orm.call("ir.attachment", "generate_access_token", [
            fileData.id,
        ]);
        return `/web/image/${fileData.id}?access_token=${accessToken}`;
    }

    /**
     * @param {string} path
     * @returns {Promise<void>}
     */
    async delete(path) {
        const attachmentId = path.split("/").pop();
        if (Number.isNaN(attachmentId)) {
            throw new Error("Invalid path: " + path);
        }
        await this.orm.unlink("ir.attachment", [parseInt(attachmentId)]);
    }
}
