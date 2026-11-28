import { canRequestAllocation } from "@hr_holidays/utils";
import { onWillStart, providePlugins, usePlugin } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { TimeOffPlugin } from "../time_off_plugin";

export class TimeOffKanbanController extends KanbanController {
    setup() {
        super.setup();

        providePlugins([TimeOffPlugin]);

        this.timeOffPlugin = usePlugin(TimeOffPlugin);
    }

    afterExecuteActionButton(clickParams) {
        super.afterExecuteActionButton(clickParams);

        this.timeOffPlugin.updateDashboard();
    }
}

export class AllocationKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.canRequestAllocation = true;
        onWillStart(async () => {
            if (this.props.archInfo.activeActions.create) {
                this.canRequestAllocation = await canRequestAllocation(this.orm);
            }
        });
    }

    get canCreate() {
        return super.canCreate && this.canRequestAllocation;
    }

    get canQuickCreate() {
        return this.canCreate && super.canQuickCreate;
    }
}
