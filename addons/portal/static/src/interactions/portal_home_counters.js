import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { range } from "@web/core/utils/numbers";
import { Interaction } from "@web/public/interaction";
import { pick } from "@web/core/utils/objects";

export class PortalHomeCounters extends Interaction {
    static selector = ".o_portal_my_home";

    async willStart() {
        return this.updateCounters();
    }

    /**
     * Return a list of counters name linked to a line that we want to keep
     * regardless of the number of documents present
     * @returns {Array}
     */
    getCountersAlwaysDisplayed() {
        return [];
    }

    async updateCounters() {
        const needed = Object.fromEntries(
            Array.from(this.el.querySelectorAll("[data-placeholder_count]")).map(
                (documentsCounterEl) => [
                    documentsCounterEl.dataset["placeholder_count"],
                    documentsCounterEl.dataset["category"],
                ]
            )
        );
        const neededKeys = Object.keys(needed);
        const numberRpc = Math.min(Math.ceil(neededKeys.length / 5), 3); // max 3 rpc, up to 5 counters by rpc ideally
        const counterByRpc = Math.ceil(neededKeys.length / numberRpc);
        const countersAlwaysDisplayed = this.getCountersAlwaysDisplayed();

        const proms = range(Math.min(numberRpc, neededKeys.length)).map(async (i) => {
            const documentsCountersData = await rpc("/my/counters", {
                counters: pick(needed, ...neededKeys.slice(i * counterByRpc, (i + 1) * counterByRpc)),
            });
            Object.keys(documentsCountersData).forEach((counterName) => {
                const documentsCounterEl = this.el.querySelector(
                    `[data-placeholder_count='${counterName}']`
                );
                documentsCounterEl.textContent = documentsCountersData[counterName];
                // The element is hidden by default, only show it if its counter is > 0 or if it's in the list of counters always shown
                if (
                    documentsCountersData[counterName] !== 0 ||
                    countersAlwaysDisplayed.includes(counterName)
                ) {
                    const cardEl = documentsCounterEl.closest(".o_portal_index_card");
                    if (cardEl.dataset.showInPortal !== "false") {
                        documentsCounterEl.classList.remove("d-none");
                        cardEl.classList.remove("d-none");
                    }
                }
            });
            return documentsCountersData;
        });
        return Promise.all(proms).then((results) => {
            this.el.querySelector(".o_portal_doc_spinner").remove();
        });
    }
}

registry.category("public.interactions").add("portal.portal_home_counters", PortalHomeCounters);
