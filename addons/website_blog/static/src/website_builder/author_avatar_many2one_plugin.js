import { patch } from "@web/core/utils/patch";
import { Many2OneAction } from "@html_builder/plugins/many2one_option_plugin";

patch(Many2OneAction, {
    dependencies: [...Many2OneAction.dependencies, "history"],
});

patch(Many2OneAction.prototype, {
    apply(args) {
        super.apply(args);
        const { editingElement, value } = args;
        const { id } = JSON.parse(value);
        const { oeId, oeField } = editingElement.dataset;

        if (oeField === "author_id") {
            for (const node of this.editable.querySelectorAll(
                `[data-oe-model="blog.post"][data-oe-id="${oeId}"][data-oe-field="author_avatar"]`
            )) {
                node.querySelector("img").src = `/web/image/res.partner/${id}/avatar_1024`;
            }
        }
    },
});
