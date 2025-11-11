import { registry } from "@web/core/registry";
import { DummySnippet } from "./dummy_snippet";

const DummySnippetEdit = (I) =>
    class extends I {
        setup() {
            super.setup();
            const targetNode = this.el;

            // Define the callback for the observer
            const callback = (mutationsList, observer) => {
                for (const mutation of mutationsList) {
                    console.log("Mutation detected:", mutation);
                }
            };

            // Create the observer instance
            this.observer = new MutationObserver(callback);

            // Observer configuration
            const config = {
                childList: true,
                subtree: true,
                attributes: true,
                characterData: true,
            };

            // Start observing the target node
            this.observer.observe(targetNode, config);

            console.log("MutationObserver started for:", targetNode);
        }

        destroy() {
            if (this.observer) {
                this.observer.disconnect();
                console.log("MutationObserver disconnected");
            }
            super.destroy();
        }
    };

registry.category("public.interactions.edit").add("website.dummy_snippet", {
    Interaction: DummySnippet,
    mixin: DummySnippetEdit,
});
