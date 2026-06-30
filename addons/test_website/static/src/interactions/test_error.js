import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { rpc } from "@web/core/network/rpc";

export class TestError extends Interaction {
    static selector = ".rpc_error a";
    dynamicContent = {
        _root: { "t-on-click.prevent": () => rpc(this.el.getAttribute("href")) },
    }
}

registry
    .category("public.interactions")
    .add("test_website.test_error", TestError);
