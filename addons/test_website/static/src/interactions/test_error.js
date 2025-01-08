import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { rpc } from "@web/core/network/rpc";

export class TestError extends Interaction {
    static selector = ".rpc_error";
    dynamicContent = {
        "a": {
            "t-on-click.prevent.withTarget": (ev, currentTargetEl) => rpc(currentTargetEl.getAttribute("href")),
        },
    }
}

registry
    .category("public.interactions")
    .add("test_website.test_error", TestError);
