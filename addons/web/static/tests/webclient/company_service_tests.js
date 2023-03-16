/** @odoo-module **/

import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { companyService } from "@web/webclient/company_service";
import { makeTestEnv } from "../helpers/mock_env";

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
