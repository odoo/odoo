/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { companyService } from "@web/webclient/company_service";
import { makeTestEnv } from "../helpers/mock_env";
import { patchWithCleanup } from "../helpers/utils";

const serviceRegistry = registry.category("services");

QUnit.module("company service");

QUnit.test("reload webclient when updating a res.company", async (assert) => {
    serviceRegistry.add("company", companyService);
    serviceRegistry.add("orm", ormService);
    serviceRegistry.add("action", {
        start(env) {
            return {
                doAction(action) {
                    assert.step(action);
                },
            };
        },
    });
    const env = await makeTestEnv();
    assert.verifySteps([]);
    await env.services.orm.read("res.company", [32]);
    assert.verifySteps([]);
    await env.services.orm.unlink("res.company", [32]);
    assert.verifySteps(["reload_context"]);
    await env.services.orm.unlink("notacompany", [32]);
    assert.verifySteps([]);
});

QUnit.test(
    "do not reload webclient when updating a res.company, but there is an error",
    async (assert) => {
        serviceRegistry.add("company", companyService);
        serviceRegistry.add("orm", ormService);
        serviceRegistry.add("action", {
            start(env) {
                return {
                    doAction(action) {
                        assert.step(action);
                    },
                };
            },
        });
        const env = await makeTestEnv();
        assert.verifySteps([]);
        env.bus.trigger("RPC:RESPONSE", {
            data: { params: { model: "res.company", method: "write" } },
            settings: {},
            result: {},
        });
        assert.verifySteps(["reload_context"]);
        env.bus.trigger("RPC:RESPONSE", {
            data: { params: { model: "res.company", method: "write" } },
            settings: {},
            error: {},
        });
        assert.verifySteps([]);
    }
);

QUnit.test("extract allowed company ids from url hash", async (assert) => {
    patchWithCleanup(session.user_companies, {
        allowed_companies: {
            1: { id: 1, name: "Company 1", sequence: 1, parent_id: false, child_ids: [] },
            2: { id: 2, name: "Company 2", sequence: 2, parent_id: false, child_ids: [] },
            3: { id: 3, name: "Company 3", sequence: 3, parent_id: false, child_ids: [] },
        },
    });

    serviceRegistry.add("company", companyService);

    Object.assign(browser.location, { hash: "cids=3-1" });
    let env = await makeTestEnv();
    assert.deepEqual(
        Object.values(env.services.company.allowedCompanies).map((c) => c.id),
        [1, 2, 3]
    );
    assert.deepEqual(env.services.company.activeCompanyIds, [3, 1]);
    assert.strictEqual(env.services.company.currentCompany.id, 3);

    // backward compatibility
    registry.category("error_handlers").remove("accessErrorHandlerCompanies");
    Object.assign(browser.location, { hash: "cids=3%2C1" });
    env = await makeTestEnv();
    assert.deepEqual(env.services.company.activeCompanyIds, [3, 1]);
    assert.strictEqual(env.services.company.currentCompany.id, 3);
});
