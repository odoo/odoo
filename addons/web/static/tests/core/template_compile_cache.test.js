// @ts-check

import { after, describe, expect, getFixture, test } from "@odoo/hoot";
import { App, Component, xml } from "@odoo/owl";
import { cacheScope, TemplateCompileCache } from "@web/core/template_compile_cache";

describe.current.tags("headless");

function makeDb(initial = {}) {
    const store = { ...initial };
    return {
        store,
        async readAll() {
            return { ...store };
        },
        async write(_table, key, value) {
            store[key] = value;
        },
    };
}

class Greeting extends Component {
    static props = ["who"];
    static template = xml`<p class="greeting">Hello <t t-esc="props.who"/>!</p>`;
}

/**
 * @param {TemplateCompileCache} cache
 * @param {string} who
 */
async function mountThrough(cache, who) {
    const app = /** @type {any} */ (new App(Greeting, { props: { who }, test: true }));
    let compiled = 0;
    const compile = app._compileTemplate;
    app._compileTemplate = function (name, template) {
        compiled++;
        return compile.call(this, name, template);
    };
    cache.install(app);
    const target = document.createElement("div");
    getFixture().append(target);
    await app.mount(target);
    after(() => app.destroy());
    return { html: target.innerHTML, compiled: () => compiled };
}

test("the key is a function of the template text and the scope", () => {
    const cache = new TemplateCompileCache({ db: null, scope: "owl/en_US/abc" });
    const key = cache.key(`<p>Hello</p>`);
    expect(key).toMatch(/^owl\/en_US\/abc\//);
    expect(cache.key(`<p>Hello</p>`)).toBe(key);
    expect(cache.key(`<p>Hello!</p>`)).not.toBe(key);
    const element = document.createElement("p");
    element.textContent = "Hello";
    expect(cache.key(element)).toBe(key);
});

test("a miss compiles and stores; a hit renders the same without compiling", async () => {
    const db = makeDb();
    const first = new TemplateCompileCache({ db, scope: "s" });
    await first.ready;
    const cold = await mountThrough(first, "world");
    expect(cold.html).toBe(`<p class="greeting">Hello world!</p>`);
    expect(cold.compiled()).toBe(1);
    expect(first.misses).toBe(1);
    expect(first.hits).toBe(0);
    expect(Object.keys(db.store)).toHaveLength(1);

    const second = new TemplateCompileCache({ db, scope: "s" });
    await second.ready;
    const warm = await mountThrough(second, "again");
    expect(warm.html).toBe(`<p class="greeting">Hello again!</p>`);
    expect(warm.compiled()).toBe(0);
    expect(second.hits).toBe(1);
    expect(second.misses).toBe(0);
});

test("only entries of the cache's scope are loaded", async () => {
    const db = makeDb({ "old/x": "return () => null;", "new/y": "return () => null;" });
    const cache = new TemplateCompileCache({ db, scope: "new" });
    await cache.ready;
    expect([...cache.code.keys()]).toEqual(["new/y"]);
});

test("a database that fails leaves a cache that only compiles", async () => {
    const db = {
        async readAll() {
            throw new Error("quota");
        },
        async write() {
            throw new Error("quota");
        },
    };
    const cache = new TemplateCompileCache({ db, scope: "s" });
    await cache.ready;
    const result = await mountThrough(cache, "anyway");
    expect(result.html).toBe(`<p class="greeting">Hello anyway!</p>`);
    expect(result.compiled()).toBe(1);
    expect(cache.code.size).toBe(1);
});

test("the scope names OWL, the language and the translations in effect", () => {
    expect(cacheScope({ code: "fr_FR", translationsHash: "h1" }, "2.8.3")).toBe(
        "2.8.3/fr_FR/h1",
    );
    expect(cacheScope({ code: "en_US" }, "2.8.3")).toBe("2.8.3/en_US/-");
});
