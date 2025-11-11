import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class DummySnippet extends Interaction {
    static selector = ".s_dummy_snippet";
}

registry.category("public.interactions").add("website.dummy_snippet", DummySnippet);
