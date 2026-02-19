import { createPublicRoot } from "./public_root";
import lazyloader from "@web/legacy/js/public/lazyloader";

lazyloader.registerPageReadinessDelay(createPublicRoot());
