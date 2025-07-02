import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import wUtils from "@website/js/utils";

export class UrlSource {
    async loadOptionsSource(term) {
        const {
            component, targetElement, onSelect
        } = this;
        const makeItem = (item) => ({
            cssClass: "ui-autocomplete-item",
            label: item.label,
            onSelect: onSelect.bind(component, item.value),
            data: { icon: item.icon || false, isCategory: false },
        });
    
        if (term[0] === "#") {
            const anchors = await wUtils.loadAnchors(
                term,
                targetElement.ownerDocument.body
            );
            return anchors.map((anchor) => makeItem({ label: anchor, value: anchor }), component);
        } else if (term.startsWith("http") || term.length === 0) {
            // avoid useless call to /website/get_suggested_links
            return [];
        }
        const res = await rpc("/website/get_suggested_links", {
            needle: term,
            limit: 15,
        });
        const choices = [];
        for (const page of res.matching_pages) {
            choices.push(makeItem(page));
        }
        for (const other of res.others) {
            if (other.values.length) {
                choices.push({
                    cssClass: "ui-autocomplete-category",
                    label: other.title,
                    data: { icon: false, isCategory: true },
                });
                for (const page of other.values) {
                    choices.push(makeItem(page));
                }
            }
        }
        return choices;
    }
}

export const urlSourceService = {
    async: [
        "loadOptionsSource",
    ],
    start() {
        return new UrlSource();
    },
};

registry.category("services").add("website_url_source", urlSourceService);
