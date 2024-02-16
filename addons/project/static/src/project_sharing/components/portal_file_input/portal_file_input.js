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
            model: res_model,
            id: res_id,
            ...otherParams
        } = super.httpParams;
        return {
            res_model,
            res_id,
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
                        file,
                        name: file.name,
                        ...otherParams,
                    })
            )
        );
        return filesData;
    }
}
