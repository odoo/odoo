import { whenReady } from "@odoo/owl";
import { selfOrderIndex as Index } from "./self_order_index";
import { mountComponent } from "@web/env";

whenReady(() => mountComponent(Index, document.body));
