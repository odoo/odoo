import { StateFileModel } from "@html_editor/others/embedded_components/core/file/state_file_model";
import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

patch(StateFileModel.prototype, {
    get defaultSource() {
        if (this.isText && this.id) {
            return url(`/mail/attachment/render_text/${this.id}`, this.urlQueryParams);
        }
        return super.defaultSource;
    },
});
