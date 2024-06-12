/** @odoo-module **/

import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { session } from "@web/session";
import { ReportAction } from "@web/webclient/actions/reports/report_action";
import { clearRegistryWithCleanup } from "@web/../tests/helpers/mock_env";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import {
    mockDownload,
    nextTick,
    patchWithCleanup,
    getFixture,
    click,
} from "@web/../tests/helpers/utils";
import {
    createWebClient,
    doAction,
    getActionManagerServerData,
} from "@web/../tests/webclient/helpers";
import { downloadReport } from "@web/webclient/actions/reports/utils";
import { registerCleanup } from "../../../helpers/cleanup";

let serverData;
let target;

const serviceRegistry = registry.category("services");

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        target = getFixture();
        clearRegistryWithCleanup(registry.category("main_components"));
        registerCleanup(() => {
            delete downloadReport.wkhtmltopdfStatusProm;
        });
    });

    QUnit.module("Report actions");

    QUnit.test("can execute report actions from db ID", async function (assert) {
        assert.expect(6);
        mockDownload((options) => {
            assert.step(options.url);
            return Promise.resolve();
        });
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
            if (route === "/report/check_wkhtmltopdf") {
                return Promise.resolve("ok");
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 7, { onClose: () => assert.step("on_close") });
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "/report/check_wkhtmltopdf",
            "/report/download",
            "on_close",
        ]);
    });

    QUnit.test("report actions can close modals and reload views", async function (assert) {
        assert.expect(8);
        mockDownload((options) => {
            assert.step(options.url);
            return Promise.resolve();
        });
        const mockRPC = async (route) => {
            if (route === "/report/check_wkhtmltopdf") {
                return Promise.resolve("ok");
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 5, { onClose: () => assert.step("on_close") });
        assert.containsOnce(
            document.body,
            ".o_technical_modal .o_form_view",
            "should have rendered a form view in a modal"
        );
        await doAction(webClient, 7, { onClose: () => assert.step("on_printed") });
        assert.containsOnce(
            document.body,
            ".o_technical_modal .o_form_view",
            "The modal should still exist"
        );
        await doAction(webClient, 11);
        assert.containsNone(
            document.body,
            ".o_technical_modal .o_form_view",
            "the modal should have been closed after the action report"
        );
        assert.verifySteps(["/report/download", "on_printed", "/report/download", "on_close"]);
    });

    QUnit.test(
        "should trigger a notification if wkhtmltopdf is to upgrade",
        async function (assert) {
            serviceRegistry.add(
                "notification",
                makeFakeNotificationService(
                    () => {
                        assert.step("notify");
                    },
                    () => {}
                )
            );
            mockDownload((options) => {
                assert.step(options.url);
                return Promise.resolve();
            });
            const mockRPC = async (route, args) => {
                assert.step((args && args.method) || route);
                if (route === "/report/check_wkhtmltopdf") {
                    return Promise.resolve("upgrade");
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 7);
            assert.verifySteps([
                "/web/webclient/load_menus",
                "/web/action/load",
                "/report/check_wkhtmltopdf",
                "/report/download",
                "notify",
            ]);
        }
    );

    QUnit.test(
        "should open the report client action if wkhtmltopdf is broken",
        async function (assert) {
            mockDownload(() => {
                assert.step("download"); // should not be called
                return Promise.resolve();
            });
            serviceRegistry.add(
                "notification",
                makeFakeNotificationService(
                    () => {
                        assert.step("notify");
                    },
                    () => {}
                )
            );
            const mockRPC = async (route, args) => {
                assert.step(args.method || route);
                if (route === "/report/check_wkhtmltopdf") {
                    return Promise.resolve("broken");
                }
                if (route.includes("/report/html/some_report")) {
                    return Promise.resolve(true);
                }
            };
            // patch the report client action to override its iframe's url so that
            // it doesn't trigger an RPC when it is appended to the DOM (for this
            // usecase, using removeSRCAttribute doesn't work as the RPC is
            // triggered as soon as the iframe is in the DOM, even if its src
            // attribute is removed right after)
            patchWithCleanup(ReportAction.prototype, {
                setup() {
                    super.setup(...arguments);
                    this.env.services.rpc(this.reportUrl);
                    this.reportUrl = "about:blank";
                },
            });
            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 7);
            assert.containsOnce(
                target,
                ".o_content iframe",
                "should have opened the report client action"
            );
            // the control panel has the content twice and a d-none class is toggled depending the screen size
            assert.containsOnce(
                target,
                ":not(.d-none) > button[title='Print']",
                "should have a print button"
            );
            assert.verifySteps([
                "/web/webclient/load_menus",
                "/web/action/load",
                "/report/check_wkhtmltopdf",
                "notify",
                // context={"lang":'en',"uid":7,"tz":'taht'}
                "/report/html/some_report?context=%7B%22lang%22%3A%22en%22%2C%22uid%22%3A7%2C%22tz%22%3A%22taht%22%7D",
            ]);
        }
    );

    QUnit.test("send context in case of html report", async function (assert) {
        assert.expect(5);
        mockDownload(() => {
            assert.step("download"); // should not be called
            return Promise.resolve();
        });
        serviceRegistry.add(
            "notification",
            makeFakeNotificationService(
                (message, options) => {
                    assert.step(options.type || "notification");
                },
                () => {}
            )
        );
        patchWithCleanup(session.user_context, { some_key: 2 });
        const mockRPC = async (route, args) => {
            assert.step(args.method || route);
            if (route.includes("/report/html/some_report")) {
                return Promise.resolve(true);
            }
        };
        // patch the report client action to override its iframe's url so that
        // it doesn't trigger an RPC when it is appended to the DOM (for this
        // usecase, using removeSRCAttribute doesn't work as the RPC is
        // triggered as soon as the iframe is in the DOM, even if its src
        // attribute is removed right after)
        patchWithCleanup(ReportAction.prototype, {
            setup() {
                super.setup(...arguments);
                this.env.services.rpc(this.reportUrl);
                this.reportUrl = "about:blank";
            },
        });
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 12);
        assert.containsOnce(target, ".o_content iframe", "should have opened the client action");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            // context={"lang":'en',"uid":7,"tz":'taht',"some_key":2}
            "/report/html/some_report?context=%7B%22lang%22%3A%22en%22%2C%22uid%22%3A7%2C%22tz%22%3A%22taht%22%2C%22some_key%22%3A2%7D",
        ]);
    });

    QUnit.test(
        "UI unblocks after downloading the report even if it threw an error",
        async function (assert) {
            assert.expect(8);
            let timesDownloasServiceHasBeenCalled = 0;
            mockDownload(() => {
                if (timesDownloasServiceHasBeenCalled === 0) {
                    assert.step("successful download");
                    timesDownloasServiceHasBeenCalled++;
                    return Promise.resolve();
                }
                if (timesDownloasServiceHasBeenCalled === 1) {
                    assert.step("failed download");
                    return Promise.reject();
                }
            });
            serviceRegistry.add("ui", uiService);
            const mockRPC = async (route) => {
                if (route === "/report/check_wkhtmltopdf") {
                    return Promise.resolve("ok");
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            const ui = webClient.env.services.ui;
            const onBlock = () => {
                assert.step("block");
            };
            const onUnblock = () => {
                assert.step("unblock");
            };
            ui.bus.addEventListener("BLOCK", onBlock);
            ui.bus.addEventListener("UNBLOCK", onUnblock);
            await doAction(webClient, 7);
            try {
                await doAction(webClient, 7);
            } catch {
                assert.step("error caught");
            }
            assert.verifySteps([
                "block",
                "successful download",
                "unblock",
                "block",
                "failed download",
                "unblock",
                "error caught",
            ]);
            ui.bus.removeEventListener("BLOCK", onBlock);
            ui.bus.removeEventListener("UNBLOCK", onUnblock);
        }
    );

    QUnit.test("can use custom handlers for report actions", async function (assert) {
        assert.expect(8);
        mockDownload((options) => {
            assert.step(options.url);
            return Promise.resolve();
        });
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
            if (route === "/report/check_wkhtmltopdf") {
                return "ok";
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        let customHandlerCalled = false;
        registry.category("ir.actions.report handlers").add("custom_handler", async (action) => {
            if (action.id === 7 && !customHandlerCalled) {
                customHandlerCalled = true;
                assert.step("calling custom handler");
                return true;
            }
            assert.step("falling through to default handler");
        });
        await doAction(webClient, 7);
        assert.step("first doAction finished");
        await doAction(webClient, 7);

        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "calling custom handler",
            "first doAction finished",
            "falling through to default handler",
            "/report/check_wkhtmltopdf",
            "/report/download",
        ]);
    });

    QUnit.test("context is correctly passed to the client action report", async (assert) => {
        assert.expect(9);

        mockDownload((options) => {
            assert.step(options.url);
            assert.deepEqual(
                options.data.context,
                `{"lang":"en","uid":7,"tz":"taht","rabbia":"E Tarantella","active_ids":[99]}`
            );
            assert.deepEqual(JSON.parse(options.data.data), [
                "/report/pdf/ennio.morricone/99",
                "qweb-pdf",
            ]);
            return Promise.resolve();
        });
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
            if (route === "/report/check_wkhtmltopdf") {
                return "ok";
            }
            if (route.includes("/report/html")) {
                return true;
            }
        };

        patchWithCleanup(ReportAction.prototype, {
            setup() {
                super.setup(...arguments);
                this.env.services.rpc(this.reportUrl);
                this.reportUrl = "about:blank";
            },
        });
        const webClient = await createWebClient({ serverData, mockRPC });

        const action = {
            context: {
                rabbia: "E Tarantella",
                active_ids: [99],
            },
            data: null,
            name: "Ennio Morricone",
            report_name: "ennio.morricone",
            report_type: "qweb-html",
            type: "ir.actions.report",
        };
        assert.verifySteps(["/web/webclient/load_menus"]);

        await doAction(webClient, action);
        assert.verifySteps([
            "/report/html/ennio.morricone/99?context=%7B%22lang%22%3A%22en%22%2C%22uid%22%3A7%2C%22tz%22%3A%22taht%22%7D",
        ]);
        await click(
            target.querySelector(
                ".o_control_panel_main_buttons .d-none.d-xl-inline-flex button[title='Print']"
            )
        );
        assert.verifySteps(["/report/check_wkhtmltopdf", "/report/download"]);
    });

    QUnit.test("url is valid", async (assert) => {
        assert.expect(2);

        patchWithCleanup(ReportAction.prototype, {
            init() {
                super.init(...arguments);
                this.reportUrl = "about:blank";
            },
        });

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, 12); // 12 is a html report action in serverData
        await nextTick();
        const hash = webClient.router.current.hash;
        // used to put report.client_action in the url
        assert.strictEqual(hash.action === "report.client_action", false);
        assert.strictEqual(hash.action === 12, true);
    });
});
