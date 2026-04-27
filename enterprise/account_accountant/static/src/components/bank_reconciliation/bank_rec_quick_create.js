import { KanbanRecordQuickCreate, KanbanQuickCreateController } from "@web/views/kanban/kanban_record_quick_create";

export class BankRecQuickCreateController extends KanbanQuickCreateController {
    static template = "account.BankRecQuickCreateController";
}

export class BankRecQuickCreate extends KanbanRecordQuickCreate {
    static template = "account.BankRecQuickCreate";
    static props = {
        ...Object.fromEntries(Object.entries(KanbanRecordQuickCreate.props).filter(([k, v]) => k !== 'group')),
        globalState: { type: Object, optional: true },
    };
    static components = { BankRecQuickCreateController };

    /**
    Overriden.
    **/
    async getQuickCreateProps(props) {
        await super.getQuickCreateProps({...props,
            group: {
                resModel: props.globalState.quickCreateState.resModel,
                context: props.globalState.quickCreateState.context,
            }
        });
    }
}
