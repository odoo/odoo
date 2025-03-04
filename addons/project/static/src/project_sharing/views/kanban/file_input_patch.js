import { FileInput } from "@web/core/file_input/file_input";
import { patch } from "@web/core/utils/patch";

patch(FileInput,{
    defaultProps: {
        ...FileInput.defaultProps,
        route: "/project/controllers/upload_attachment",

    }
});
