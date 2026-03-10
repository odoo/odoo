/** @odoo-module*/
import {registry} from "@web/core/registry";
import {download} from "@web/core/network/download";
import { BlockUI, unblockUI } from "@web/core/ui/block_ui";
// Action manager for xlsx report
registry.category('ir.actions.report handlers').add('xlsx', async (action) => {
    if (action.report_type === 'xlsx'){
       BlockUI;
        await download({
            url : '/xlsx_report',
            data : action.data,
            error : (error) => self.call('crash_manager', 'rpc_error', error),
            complete: () => unblockUI,
        });
    }
})
