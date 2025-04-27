import { whenReady } from "@odoo/owl";
import { mountComponent } from "@web/env";
import { Playground } from "./playground";

const config = {
    dev: true,
    name: "Owl Tutorial",
};

// Mount the Playground component when the document.body is ready
whenReady(() => mountComponent(Playground, document.body, config));
