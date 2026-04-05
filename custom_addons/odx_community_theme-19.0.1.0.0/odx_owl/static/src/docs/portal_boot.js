/** @odoo-module **/

import { whenReady } from "@odoo/owl";
import { mountComponent } from "@web/env";
import { OdxOwlDocsApp } from "@odx_owl/docs/docs_app";

whenReady(async () => {
    const target = document.getElementById("odx_owl_frontend_root");
    if (!target) {
        return;
    }
    await mountComponent(OdxOwlDocsApp, target, {
        name: "ODX OWL Frontend",
        props: {
            mode: target.dataset.mode || "frontend",
        },
    });
});
