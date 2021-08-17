/** @odoo-module **/

import { useDebugCategory } from "@web/core/debug/debug_context";
import { useSetupAction } from "@web/webclient/actions/action_hook";
import { registry } from "@web/core/registry";

const { useComponent } = owl.hooks;

export function useSetupView(params) {
    const component = useComponent();
    useDebugCategory("view", { component });
    useSetupAction(params);
}

export function useViewArch(arch, params = {}) {
    const CATEGORY = "__processed_archs__";

    arch = arch.trim();
    const processedRegistry = registry.category(CATEGORY);

    let processedArch;
    if (!processedRegistry.contains(arch)) {
        processedArch = {};
        processedRegistry.add(arch, processedArch);
    } else {
        processedArch = processedRegistry.get(arch);
    }

    const { compile, extract } = params;
    if (!("template" in processedArch) && compile) {
        processedArch.template = owl.tags.xml`${compile(arch)}`;
    }
    if (!("extracted" in processedArch) && extract) {
        processedArch.extracted = extract(arch);
    }

    return processedArch;
}
