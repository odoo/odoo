import { describe, expect, test } from "@odoo/hoot";
import { click, queryOne } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

setupInteractionWhiteList([
    "website_sale.tracking",
    "website_sale.product_card_tracking",
    "website_sale.promotion_tracking",
]);
describe.current.tags("interaction_dev");

function setupTracking() {
    const events = [];
    const observers = [];
    patchWithCleanup(window, {
        gtag: (command, name, data) => events.push({ command, name, data }),
        IntersectionObserver: class {
            constructor(callback) { this.callback = callback; }
            observe(element) { observers.push({ element, callback: this.callback }); }
            disconnect() {}
        },
    });
    return { events, observers };
}

const product = { item_id: "SKU-1", item_name: "Test product", price: 15 };
const promotion = { promotion_id: "7", promotion_name: "Summer sale", items: [product] };

test("product list impressions require visibility and preserve item data", async () => {
    const { events, observers } = setupTracking();
    await startInteractions(`<div class="oe_website_sale">
        <article class="oe_product_cart" data-product-ga-currency="USD"
            data-product-tracking-info='${JSON.stringify({ ...product, item_list_name: "Shop" })}'>
            <a href="#product">Product</a><button>Add to cart</button>
        </article>
    </div>`);
    expect(events).toHaveLength(0);
    observers[0].callback([{ isIntersecting: false, intersectionRatio: 0 }]);
    expect(events).toHaveLength(0);
    observers[0].callback([{ isIntersecting: true, intersectionRatio: 1 }]);
    expect(events).toEqual([{
        command: "event", name: "view_item_list",
        data: { currency: "USD", item_list_name: "Shop", items: [product] },
    }]);
    observers[0].callback([{ isIntersecting: true, intersectionRatio: 1 }]);
    expect(events).toHaveLength(1);
    await click("article");
    await click("button");
    expect(events).toHaveLength(1);
    await click("a");
    expect(events[1].name).toBe("select_item");
    expect(events[1].data.items).toEqual([product]);
});

test("promotion impressions and selections use the advertised offer", async () => {
    const { events, observers } = setupTracking();
    await startInteractions(`<div class="oe_website_sale">
        <form data-promotion-tracking-info='${JSON.stringify(promotion)}'>
            <button type="submit">Claim reward</button>
        </form>
    </div>`);
    expect(events).toHaveLength(0);
    observers[0].callback([{ isIntersecting: true, intersectionRatio: 1 }]);
    queryOne("form").addEventListener("submit", event => event.preventDefault());
    await click("button[type=submit]");
    expect(events).toEqual([
        { command: "event", name: "view_promotion", data: promotion },
        { command: "event", name: "select_promotion", data: promotion },
    ]);
});

test("empty analytics payloads do not generate events", async () => {
    const { events, observers } = setupTracking();
    await startInteractions(`<div class="oe_website_sale">
        <article class="oe_product_cart" data-product-tracking-info='{}'><a href="#product">Product</a></article>
        <form data-promotion-tracking-info='{}'></form>
    </div>`);
    await click("a");
    queryOne("form").addEventListener("submit", event => event.preventDefault());
    queryOne("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(events).toHaveLength(0);
    expect(observers).toHaveLength(0);
});


test("banner links select promotions but blank areas do not", async () => {
    const { events } = setupTracking();
    await startInteractions(`<div class="oe_website_sale">
        <section data-promotion-tracking-info='${JSON.stringify(promotion)}'>
            <span>Offer</span><a href="#sale">View offer</a>
        </section>
    </div>`);
    await click("span");
    expect(events).toHaveLength(0);
    await click("a");
    expect(events).toEqual([{ command: "event", name: "select_promotion", data: promotion }]);
});

test("reward selection sends only the chosen product without internal mappings", async () => {
    const { events } = setupTracking();
    const other = { item_id: "OTHER", item_name: "Other gift" };
    const info = { ...promotion, items: [product, other], product_items: { "1": product, "2": other } };
    await startInteractions(`<div class="oe_website_sale">
        <form data-promotion-tracking-info='${JSON.stringify(info)}'>
            <select name="product_id"><option value="1">First</option><option value="2" selected>Second</option></select>
            <button type="submit">Claim reward</button>
        </form>
    </div>`);
    queryOne("form").addEventListener("submit", event => event.preventDefault());
    await click("button");
    expect(events).toEqual([{
        command: "event", name: "select_promotion", data: { ...promotion, items: [other] },
    }]);
});
