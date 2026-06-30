import { whenReady } from "@odoo/owl";
import { mountComponent } from "@web/env";
import { CustomerDisplay } from "./customer_display";

whenReady(() => mountComponent(CustomerDisplay, document.body));
