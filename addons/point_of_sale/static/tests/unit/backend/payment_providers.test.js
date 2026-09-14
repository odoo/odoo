import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { PosPaymentProviderCards } from "@point_of_sale/backend/pos_payment_provider_cards/pos_payment_provider_cards";
import { mockService, mountWithCleanup } from "@web/../tests/web_test_helpers";

for (const preset of ["desktop", "mobile"]) {
    describe(preset, () => {
        describe.current.tags(preset);

        async function mountCards(record, install = async () => false) {
            mockService("orm", {
                call: async (model, method) => {
                    if (method === "get_provider_status") {
                        return {
                            state: [
                                { id: 1, name: "pos_stripe", state: "uninstalled" },
                                { id: 2, name: "pos_adyen", state: "installed" },
                            ],
                        };
                    }
                    expect(method).toBe("button_immediate_install");
                    return install();
                },
            });
            return mountWithCleanup(PosPaymentProviderCards, { props: { record } });
        }

        test("activation locks before saving and releases after installation", async () => {
            const saved = new Deferred();
            const installed = new Deferred();
            let saves = 0;
            let installs = 0;
            const cards = await mountCards(
                {
                    save: () => {
                        saves++;
                        return saved;
                    },
                },
                () => {
                    installs++;
                    return installed;
                },
            );
            const pending = cards.installModule(1);
            const duplicate = cards.installModule(1);
            expect(saves).toBe(1);
            await animationFrame();
            expect("button:disabled").toHaveCount(2);
            saved.resolve(true);
            await animationFrame();
            expect(installs).toBe(1);
            installed.resolve(false);
            await Promise.all([pending, duplicate]);
            await animationFrame();
            expect("button:disabled").toHaveCount(0);
        });

        test("validation failure does not install and permits retry", async () => {
            let installs = 0;
            const cards = await mountCards({ save: async () => false }, async () => {
                installs++;
            });
            await cards.installModule(1);
            expect(installs).toBe(0);
            expect(cards.state.disabled).toBe(false);
        });

        test("installation failure releases the controls and propagates", async () => {
            const cards = await mountCards({ save: async () => true }, async () => {
                throw new Error("install failed");
            });
            await expect(cards.installModule(1)).rejects.toThrow("install failed");
            expect(cards.state.disabled).toBe(false);
        });

        test("provider setup awaits the record update", async () => {
            const updated = new Deferred();
            let complete = false;
            const cards = await mountCards({
                update: (values) => {
                    expect(values).toEqual({
                        payment_method_type: "terminal",
                        use_payment_terminal: "adyen",
                        name: "Adyen",
                    });
                    return updated;
                },
            });
            const pending = cards.setupProvider(2).then(() => {
                complete = true;
            });
            await animationFrame();
            expect(complete).toBe(false);
            updated.resolve();
            await pending;
            expect(complete).toBe(true);
        });

        test("only installed providers can be configured", async () => {
            let updates = 0;
            const cards = await mountCards({
                update: async () => {
                    updates++;
                },
            });
            await cards.setupProvider(1);
            await cards.setupProvider(999);
            expect(updates).toBe(0);
            await cards.setupProvider(2);
            expect(updates).toBe(1);
        });
    });
}
