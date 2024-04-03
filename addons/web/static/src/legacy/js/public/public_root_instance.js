/** @odoo-module alias=root.widget */
import { PublicRoot, createPublicRoot } from "./public_root";
import lazyloader from "web.public.lazyloader";

const prom = createPublicRoot(PublicRoot);
lazyloader.registerPageReadinessDelay(prom);
export default prom;
