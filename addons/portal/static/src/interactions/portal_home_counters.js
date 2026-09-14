/** @odoo-module native */
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class PortalHomeCounters extends Interaction {
    static selector = ".o_portal_my_home";

    async willStart() {
        return this.updateCounters();
    }

    /**
     * @returns {Array}
     */
    getCountersAlwaysDisplayed() {
        return [];
    }

    async updateCounters() {
        const elementsByCounter = new Map();
        for (const element of this.el.querySelectorAll("[data-placeholder_count]")) {
            const name = element.dataset.placeholder_count;
            if (!elementsByCounter.has(name)) {
                elementsByCounter.set(name, []);
            }
            elementsByCounter.get(name).push(element);
        }
        const needed = [...elementsByCounter.keys()];
        const numberRpc = Math.min(Math.ceil(needed.length / 5), 3);
        const counterByRpc = Math.ceil(needed.length / (numberRpc || 1));
        const countersAlwaysDisplayed = this.getCountersAlwaysDisplayed();

        const proms = [...Array(Math.min(numberRpc, needed.length)).keys()].map(
            async (i) => {
                const documentsCountersData = await this.waitFor(
                    rpc("/my/counters", {
                        counters: needed.slice(
                            i * counterByRpc,
                            (i + 1) * counterByRpc,
                        ),
                    }),
                );
                for (const [counterName, count] of Object.entries(
                    documentsCountersData,
                )) {
                    for (const element of elementsByCounter.get(counterName) || []) {
                        element.textContent = count;
                        element
                            .closest(".o_portal_index_card")
                            ?.classList.toggle(
                                "d-none",
                                count === 0 &&
                                    !countersAlwaysDisplayed.includes(counterName),
                            );
                    }
                }
                return documentsCountersData;
            },
        );
        return Promise.all(proms).finally(() => {
            this.el.querySelector(".o_portal_doc_spinner")?.remove();
        });
    }
}

registry
    .category("public.interactions")
    .add("portal.portal_home_counters", PortalHomeCounters);
