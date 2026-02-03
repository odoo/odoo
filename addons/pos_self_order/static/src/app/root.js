import { mount, whenReady, reactive } from "@odoo/owl";
import { selfOrderIndex as Index } from "./self_order_index";
import { mountComponent } from "@web/env";
import { Loader } from "@point_of_sale/app/components/loader/loader";
import { getTemplate } from "@web/core/templates";

whenReady(async () => {
    try {
        await mountComponent(Index, document.body);
    } catch (err) {
        const loader = reactive({ isShown: true, error: err });
        mount(Loader, document.body, {
            getTemplate,
            props: { loader },
            translatableAttributes: ["data-tooltip"],
            trsnalteFn: (s) => s,
        });
        console.log(err);
    }
});
