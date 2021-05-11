/** @odoo-module **/

import { useDebugMenu } from "@web/core/debug/debug_menu";
import { useSetupAction } from "@web/webclient/actions/action_hook";

const { useComponent } = owl.hooks;

export function useSetupView(params) {
    const component = useComponent();
    useDebugMenu("view", { component });
    useSetupAction(params);
}
