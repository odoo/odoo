/** @odoo-module */

import { FileInput } from '@web/core/file_input/file_input';

export class PortalFileInput extends FileInput {
    static props = {
        ...FileInput.props,
        accessToken: { type: String, optional: true },
    };
    static defaultProps = {
        ...FileInput.defaultProps,
        accessToken: "",
    };

    /**
     * @override
     */
    get httpParams() {
        const {
            model: thread_model,
            id: thread_id,
            ...otherParams
        } = super.httpParams;
        return {
            thread_model,
            thread_id,
            access_token: this.props.accessToken,
            ...otherParams,
        }
    }

    async uploadFiles(params) {
        const { ufile: files, ...otherParams } = params;
        const filesData = await Promise.all(
            files.map(
                (file) =>
                    super.uploadFiles({
                        ufile: [file],
                        token: otherParams.access_token,
                        is_pending: true,
                        ...otherParams,
                    })
            )
        );
        return filesData;
    }
}
