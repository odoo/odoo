import { describe, destroy, expect, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { initLNA } from "@point_of_sale/app/utils/init_lna";
import { PosKanbanRenderer } from "@point_of_sale/backend/pos_kanban_view/pos_kanban_view";
import { PosPaymentProviderCards } from "@point_of_sale/backend/pos_payment_provider_cards/pos_payment_provider_cards";
import { TestEPos } from "@point_of_sale/backend/test_epos/test_epos";
import {
    contains,
    defineModels,
    fields,
    MockServer,
    mockService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";

for (const preset of ["desktop", "mobile"]) {
    describe(preset, () => {
        describe.current.tags(preset);
        async function printerWidget(useLna = false) {
            patchWithCleanup(odoo, { use_lna: false });
            mockService("orm", { call: async () => ({ use_lna: useLna }) });
            const notifications = [];
            mockService("notification", {
                add: (message, options) => notifications.push({ message, ...options }),
            });
            const printer = await mountWithCleanup(TestEPos, {
                props: { record: { data: { epson_printer_ip: "localhost" } } },
            });
            return { printer, notifications };
        }
        for (const success of ["1", "true"]) {
            test(`Epson SOAP response with success=${success}`, async () => {
                const { printer, notifications } = await printerWidget();
                patchWithCleanup(window, {
                    fetch: async () =>
                        new Response(
                            `<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><p:response xmlns:p="http://www.epson-pos.com/schemas/2011/03/epos-print" success="${success}" code="" status="2"/></s:Body></s:Envelope>`,
                        ),
                });
                await printer.onClick();
                expect(notifications.map(({ type }) => type)).toEqual(["info"]);
            });
        }
        test("closing during permission query suppresses its late notification", async () => {
            const { printer, notifications } = await printerWidget(true);
            const permission = new Deferred();
            patchWithCleanup(navigator.permissions, { query: () => permission });
            const pending = printer.onClick();
            destroy(printer);
            permission.resolve({ state: "denied" });
            await pending;
            expect(notifications).toHaveLength(0);
        });
        test("test receipt does not leave a permission watcher behind", async () => {
            const { printer, notifications } = await printerWidget(true);
            const permission = { state: "granted", onchange: null };
            patchWithCleanup(navigator.permissions, { query: async () => permission });
            patchWithCleanup(window, {
                fetch: async () => new Response('<response success="true" code=""/>'),
            });
            await printer.onClick();
            destroy(printer);
            permission.state = "denied";
            permission.onchange?.();
            expect(notifications).toHaveLength(1);
            expect(permission.onchange).toBe(null);
        });
        test("closing after response headers suppresses late body completion", async () => {
            const { printer, notifications } = await printerWidget();
            const body = new Deferred();
            patchWithCleanup(window, {
                fetch: async () => ({ ok: true, status: 200, text: () => body }),
            });
            const pending = printer.onClick();
            await animationFrame();
            destroy(printer);
            body.resolve('<response success="true" code=""/>');
            await pending;
            expect(notifications).toHaveLength(0);
        });
        test("save rejection releases the activation lock", async () => {
            mockService("orm", { call: async () => ({ state: [] }) });
            const cards = await mountWithCleanup(PosPaymentProviderCards, {
                props: {
                    record: {
                        save: async () => {
                            throw new Error("save rejected");
                        },
                    },
                },
            });
            await expect(cards.installModule(1)).rejects.toThrow("save rejected");
            expect(cards.state.disabled).toBe(false);
        });
        class PosConfig extends models.Model {
            _name = "pos.config";
            name = fields.Char();
            _records = [];
        }
        class PaymentMethod extends models.Model {
            _name = "pos.payment.method";
            name = fields.Char({ default: "Counter terminal" });
            payment_method_type = fields.Char({ default: "terminal" });
            use_payment_terminal = fields.Char();
            _records = [];
        }
        class Module extends models.Model {
            _name = "ir.module.module";
        }
        defineModels([PosConfig, PaymentMethod, Module]);
        test("scenario cannot be created again while its actual list reload is pending", async () => {
            patchWithCleanup(user, { hasGroup: async () => true });
            let renderer;
            patchWithCleanup(PosKanbanRenderer.prototype, {
                setup() {
                    super.setup();
                    renderer = this;
                },
            });
            onRpc("pos.config", "get_pos_kanban_view_state", () => ({
                has_pos_config: false,
                has_chart_template: true,
                is_restaurant_installed: true,
                is_main_company: true,
            }));
            let scenarios = 0;
            onRpc("pos.config", "load_onboarding_clothes_scenario", () => {
                scenarios++;
                MockServer.env["pos.config"].create({ name: "Shop" });
                return 1;
            });
            const reloaded = new Deferred();
            let reads = 0;
            onRpc("pos.config", "web_search_read", async ({ parent }) => {
                if (++reads > 1) {
                    await reloaded;
                }
                return parent();
            });
            await mountView({
                type: "kanban",
                resModel: "pos.config",
                arch: '<kanban js_class="pos_config_kanban_view"><templates><t t-name="card"><field name="name"/></t></templates></kanban>',
            });
            await contains(".pos-scenario-card:first").click();
            await animationFrame();
            expect(reads).toBe(2);
            expect("button.pos-scenario-card:disabled").toHaveCount(6);
            const duplicate = renderer.clickLoadScenario(renderer.shopScenarios[0]);
            await animationFrame();
            expect(scenarios).toBe(1);
            reloaded.resolve();
            await duplicate;
            await animationFrame();
        });

        test("activation remains disabled while successful installation reloads the page", async () => {
            let installs = 0;
            mockService("orm", {
                call: async (model, method) => {
                    if (method === "get_provider_status") {
                        return {
                            state: [
                                { id: 1, name: "pos_stripe", state: "uninstalled" },
                            ],
                        };
                    }
                    installs++;
                    return { type: "ir.actions.client", tag: "reload" };
                },
            });
            patchWithCleanup(browser.location, { reload: () => expect.step("reload") });
            const cards = await mountWithCleanup(PosPaymentProviderCards, {
                props: { record: { save: async () => true } },
            });
            await cards.installModule(1);
            await animationFrame();
            expect("button:disabled").toHaveCount(1);
            await cards.installModule(1);
            expect(installs).toBe(1);
            expect.verifySteps(["reload"]);
        });

        test("existing LNA callers still receive permission changes", async () => {
            patchWithCleanup(odoo, { use_lna: true });
            const permission = Object.assign(document.createElement("span"), {
                state: "granted",
            });
            patchWithCleanup(navigator.permissions, { query: async () => permission });
            const notices = [];
            await initLNA(
                { add: (message, options) => notices.push(options.type) },
                (type) => expect.step(type),
            );
            permission.state = "denied";
            permission.dispatchEvent(new Event("change"));
            expect.verifySteps(["success", "danger"]);
            expect(notices).toEqual(["warning"]);
        });

        test("LNA callback errors do not disable browser support or retry the callback", async () => {
            patchWithCleanup(odoo, { use_lna: true });
            patchWithCleanup(navigator.permissions, {
                query: async () => ({ state: "granted" }),
            });
            const notices = [];
            const states = [];
            await expect(
                initLNA({ add: (message) => notices.push(message) }, (state) => {
                    states.push(state);
                    throw new Error("callback failed");
                }),
            ).rejects.toThrow("callback failed");
            expect(odoo.use_lna).toBe(true);
            expect(notices).toEqual([]);
            expect(states).toEqual(["success"]);
        });

        test("an unsupported LNA permission still disables LNA and reports it once", async () => {
            patchWithCleanup(odoo, { use_lna: true });
            patchWithCleanup(navigator.permissions, {
                query: async () => {
                    throw new TypeError("unsupported permission");
                },
            });
            const notices = [];
            await initLNA(
                { add: (message, options) => notices.push(options.type) },
                (state) => expect.step(state),
            );
            expect(odoo.use_lna).toBe(false);
            expect(notices).toEqual(["warning"]);
            expect.verifySteps(["danger"]);
        });

        test("LNA subscriptions preserve other listeners and abort independently", async () => {
            patchWithCleanup(odoo, { use_lna: true });
            const permission = Object.assign(document.createElement("span"), {
                state: "granted",
                onchange: () => expect.step("existing"),
            });
            patchWithCleanup(navigator.permissions, { query: async () => permission });
            const first = new AbortController();
            const second = new AbortController();
            const notification = { add: () => {} };
            await initLNA(notification, (state) => expect.step(`first:${state}`), {
                signal: first.signal,
            });
            await initLNA(notification, (state) => expect.step(`second:${state}`), {
                signal: second.signal,
            });
            expect.verifySteps(["first:success", "second:success"]);
            permission.state = "prompt";
            permission.dispatchEvent(new Event("change"));
            expect.verifySteps(["existing", "first:warning", "second:warning"]);
            first.abort();
            permission.state = "granted";
            permission.dispatchEvent(new Event("change"));
            expect.verifySteps(["existing", "second:success"]);
            second.abort();
            permission.dispatchEvent(new Event("change"));
            expect.verifySteps(["existing"]);
        });

        test("onboarding accepts keyboard activation", async () => {
            patchWithCleanup(user, { hasGroup: async () => true });
            onRpc("pos.config", "get_pos_kanban_view_state", () => ({
                has_pos_config: false,
                has_chart_template: true,
                is_restaurant_installed: true,
                is_main_company: true,
            }));
            let calls = 0;
            onRpc("pos.config", "load_onboarding_clothes_scenario", () => {
                calls++;
                return 1;
            });
            await mountView({
                type: "kanban",
                resModel: "pos.config",
                arch: '<kanban js_class="pos_config_kanban_view"><templates><t t-name="card"><field name="name"/></t></templates></kanban>',
            });
            await contains(".pos-scenario-card:first").focus();
            await press("Enter");
            await animationFrame();
            expect(calls).toBe(1);
        });

        test("activation stays locked across a real new form record save", async () => {
            patchWithCleanup(user, { hasGroup: async () => true });
            onRpc("pos.payment.method", "get_provider_status", () => ({
                state: [{ id: 1, name: "pos_stripe", state: "uninstalled" }],
            }));
            const installed = new Deferred();
            let installs = 0;
            onRpc("ir.module.module", "button_immediate_install", async () => {
                installs++;
                await installed;
                return false;
            });
            await mountView({
                type: "form",
                resModel: "pos.payment.method",
                arch: `<form><field name="name"/><field name="payment_method_type"/><field name="use_payment_terminal"/><widget name="pos_payment_provider_cards" invisible="use_payment_terminal or payment_method_type != 'terminal'"/></form>`,
            });
            await contains("button:contains('Activate')").click();
            await animationFrame();
            expect(MockServer.env["pos.payment.method"].search_count([])).toBe(1);
            expect(installs).toBe(1);
            expect("button:contains('Activate')").toHaveProperty("disabled", true);
            installed.resolve();
            await animationFrame();
            expect("button:contains('Activate')").toHaveProperty("disabled", false);
        });

        test("a failed list reload releases the onboarding controls", async () => {
            patchWithCleanup(user, { hasGroup: async () => true });
            onRpc("pos.config", "get_pos_kanban_view_state", () => ({
                has_pos_config: false,
                has_chart_template: true,
                is_restaurant_installed: true,
                is_main_company: true,
            }));
            let model;
            patchWithCleanup(PosKanbanRenderer.prototype, {
                setup() {
                    super.setup();
                    model = this.props.list.model;
                },
            });
            await mountView({
                type: "kanban",
                resModel: "pos.config",
                arch: '<kanban js_class="pos_config_kanban_view"><templates><t t-name="card"><field name="name"/></t></templates></kanban>',
            });
            patchWithCleanup(model, {
                _loadData: async () => {
                    throw new Error("reload failed");
                },
            });
            await expect(model.load()).rejects.toThrow("reload failed");
            await animationFrame();
            expect(".pos-scenario-card:disabled").toHaveCount(0);
        });
    });
}
