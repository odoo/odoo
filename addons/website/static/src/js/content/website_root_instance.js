import { createPublicRoot } from "@web/public/public_root";
import lazyloader from "@web/public/lazyloader";

const prom = createPublicRoot().then(async (rootInstance) => {
    if (window.frameElement) {
        window.dispatchEvent(new CustomEvent("PUBLIC-ROOT-READY", { detail: { rootInstance } }));
    }
    return rootInstance;
});
lazyloader.registerPageReadinessDelay(prom);
export default prom;
