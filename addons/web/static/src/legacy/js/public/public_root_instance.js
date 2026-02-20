/** @odoo-module alias=root.widget */
import { PublicRoot, createPublicRoot } from "./public_root";
import { registerPageReadinessDelay } from "@web/public/lazyloader";

const prom = createPublicRoot(PublicRoot);
registerPageReadinessDelay(prom);
export default prom;
