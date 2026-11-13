import { describe, expect, test } from "@odoo/hoot";
import { definePosModels } from "../data/generate_model_definitions";
import { expectFormattedPrice, setupMultiCurrency, setupPosEnv } from "../utils";

definePosModels();

// 1 Ⓐ = 15 $ and 1 $ = 15 Ⓑ, see setupMultiCurrency
describe("convert", () => {
    test("from the company currency by default", async () => {
        const store = await setupPosEnv();
        const { xta, xtb } = setupMultiCurrency(store);

        expect(xta.convert(136.57)).toBe(9.1); // 9.104666...
        expect(xta.convert(136.6)).toBe(9.11); // 9.106666...
        expect(xtb.convert(9.11)).toBe(136.65);
    });

    test("to the company currency", async () => {
        const store = await setupPosEnv();
        const { usd, xta, xtb } = setupMultiCurrency(store);

        expect(usd.convert(9.1, xta)).toBe(136.5);
        expect(usd.convert(100, xtb)).toBe(6.67); // 6.666...
    });

    test("in the same currency only rounds", async () => {
        const store = await setupPosEnv();
        const { usd, xta } = setupMultiCurrency(store);

        expect(xta.convert(9.104, xta)).toBe(9.1);
        expect(usd.convert(136.574, usd)).toBe(136.57);
    });

    test("between two foreign currencies rounds only once", async () => {
        const store = await setupPosEnv();
        const { xtb } = setupMultiCurrency(store);
        const eur = store.models["res.currency"].get(125); // 1 $ = 0.87 €

        // 1 € = 1.149425... $ = 17.241379... Ⓑ
        // Rounding the intermediate USD amount would give 1.15 $ = 17.25 Ⓑ
        expect(xtb.convert(1, eur)).toBe(17.24);
    });
});

test("convertFormatted", async () => {
    const store = await setupPosEnv();
    const usd = store.config.currency_id;
    const eur = store.models["res.currency"].get(125); // 1 $ = 0.87 €

    expectFormattedPrice(usd.convertFormatted(87, eur), "$ 100.00");
    expectFormattedPrice(usd.convertFormatted(100), "$ 100.00");
});
