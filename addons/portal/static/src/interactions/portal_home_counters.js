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
                const documentsCounterEl = this.getCounterEl(counterName);
                const count = documentsCountersData[counterName];
                documentsCounterEl.textContent = count;
                // A card total only decides whether the card shows
                documentsCounterEl.classList.toggle("d-none", !count || documentsCounterEl.matches(".o_portal_count"));
                // The element is hidden by default, only show it if its counter is > 0
                if (count !== 0) {
                    this.showCard(documentsCounterEl);
                }
            });
            return documentsCountersData;
        });
        return Promise.all(proms).then((results) => {
            // Cards kept at zero are meant for customers, not for vendors
            const isVendor = this.el.querySelector(
                ".o_portal_index_card[data-category='vendor_category']:not(.d-none)"
            );
            if (!isVendor) {
                const counters = Object.assign({}, ...results);
                for (const counterName of countersAlwaysDisplayed) {
                    if (counters[counterName] === 0) {
                        this.showCard(this.getCounterEl(counterName));
                    }
                }
            }
            this.el.querySelector(".o_portal_doc_spinner").remove();
        });
    }

    getCounterEl(counterName) {
        return this.el.querySelector(`[data-placeholder_count='${counterName}']`);
    }

    showCard(documentsCounterEl) {
        const cardEl = documentsCounterEl.closest(".o_portal_index_card");
        if (cardEl.dataset.showInPortal !== "false") {
            cardEl.classList.remove("d-none");
        }
    }
}

registry.category("public.interactions").add("portal.portal_home_counters", PortalHomeCounters);
