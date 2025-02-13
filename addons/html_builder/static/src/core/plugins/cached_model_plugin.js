import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { Cache } from "@web/core/utils/cache";
import { ModelEdit } from "./cached_model_utils";

export class CachedModelPlugin extends Plugin {
    static id = "CachedModel";
    static shared = ["ormRead", "useModelEdit"];
    setup() {
        this.ormReadCache = new Cache(
            ({ model, ids, fields }) => this.services.orm.read(model, ids, fields),
            JSON.stringify
        );
        this.modelEditCache = new Cache(({ model, recordId }) => {
            const modelEdit = new ModelEdit(this.editable);
            modelEdit.setRecord(model, recordId);
            return modelEdit;
        }, JSON.stringify);
    }
    destroy() {
        this.ormReadCache.invalidate();
        this.modelEditCache.invalidate();
    }
    ormRead(model, ids, fields) {
        return this.ormReadCache.read({ model, ids, fields });
    }
    useModelEdit({ model, recordId, field }) {
        const modelEdit = this.modelEditCache.read({ model, recordId, field });
        // track el ?
        return modelEdit;
    }
}
registry.category("website-plugins").add(CachedModelPlugin.id, CachedModelPlugin);
