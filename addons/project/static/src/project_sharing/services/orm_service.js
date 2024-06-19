import { ORM } from "@web/core/orm_service";
import { patch } from "@web/core/utils/patch";

patch(ORM.prototype, {
    call(model, method, args = [], kwargs = {}) {
        const path = `${model}/${method}`;
        console.log(path);
        const excludePaths = [
            "ir.ui.view/render_public_asset",
            "ir.filters/create_or_replace",
        ];
        if (!excludePaths.includes(path) && !method.startsWith("project_sharing_")) {
            method = `project_sharing_${method}`;
        }
        return super.call(model, method, args, kwargs);
    },
});
