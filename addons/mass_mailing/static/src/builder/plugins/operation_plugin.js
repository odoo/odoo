import { OperationPlugin } from "@html_builder/core/operation_plugin";
import { registry } from "@web/core/registry";

export class MassMailingOperationPlugin extends OperationPlugin {
    static shared = [...OperationPlugin.shared, "getUnlockedDef"];

    /**
     * Does not throw if the editor was destroyed before the operation could be
     * completed.
     * @override
     */
    async next() {
        return super.next(...arguments).catch((error) => {
            if (!this.isDestroyed) {
                throw error;
            }
        });
    }

    getUnlockedDef() {
        return this.operation.mutex.getUnlockedDef();
    }
}

registry
    .category("mass_mailing-plugins")
    .add(MassMailingOperationPlugin.id, MassMailingOperationPlugin);
