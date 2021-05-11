/** @odoo-module **/

import { useDebugCategory } from "@web/core/debug/debug_context";
import { useSetupAction } from "@web/webclient/actions/action_hook";

const { useComponent } = owl.hooks;

export function useSetupView(params) {
    const component = useComponent();
    useDebugCategory("view", { component });
    useSetupAction(params);
}
