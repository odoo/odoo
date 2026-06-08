import { test, describe, expect } from "@odoo/hoot";
import { scrollItemIntoViewX } from "@pos_self_order/app/utils/scroll";

const setupDomElement = ({ parentWidth, childWidth, leftMargin }) => {
    const scrollEl = document.createElement("div");
    scrollEl.style.overflowX = "auto";
    scrollEl.style.width = `${parentWidth}px`;

    const itemEl = document.createElement("div");
    itemEl.className = "item";
    itemEl.style.width = `${childWidth}px`;
    itemEl.style.marginLeft = `${leftMargin}px`;
    itemEl.textContent = "Item";

    scrollEl.appendChild(itemEl);
    document.body.appendChild(scrollEl);
    return { scrollEl, itemEl };
};

describe("scrollItemIntoViewX", () => {
    test.tags("desktop");
    test("scrolls when item is out of view", () => {
        const { scrollEl } = setupDomElement({
            parentWidth: 200,
            childWidth: 100,
            leftMargin: 300,
        });
        expect(scrollEl.scrollLeft).toBe(0);
        scrollItemIntoViewX(scrollEl, ".item", {
            align: "start",
            scrollBehavior: "auto", // animation takes time to update scroll value
        });

        expect(scrollEl.scrollLeft).toBe(200);
        scrollEl.remove();
    });

    test.tags("desktop");
    test("does not scroll if item is already visible", () => {
        const { scrollEl } = setupDomElement({
            parentWidth: 200,
            childWidth: 100,
            leftMargin: 100,
        });
        expect(scrollEl.scrollLeft).toBe(0);
        scrollItemIntoViewX(scrollEl, ".item", {
            align: "start",
            scrollBehavior: "auto", // animation takes time to update scroll value
        });

        expect(scrollEl.scrollLeft).toBe(0);
        scrollEl.remove();
    });
});
