import { createPublicRoot } from "./public_root";
import lazyloader from "@web/public/lazyloader";

lazyloader.registerPageReadinessDelay(createPublicRoot());
