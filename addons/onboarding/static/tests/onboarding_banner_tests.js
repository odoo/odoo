
/** @odoo-module **/

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    getFixture,
    mount,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { OnboardingBanner } from "@web/views/onboarding_banner";
import { View } from "@web/views/view";
import { session } from "@web/session";

import { Component, xml } from "@odoo/owl";

const viewRegistry = registry.category("views");
let serverData;
let target;

QUnit.module("Onboarding banner", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                animal: {
                    fields: {
                        name: { string: "name", type: "string" },
                    },
                },
            },
            views: {
                "animal,1,toy": `
                    <toy banner_route="/onboarding/animal">
                        <Banner t-if="env.config.bannerRoute" />
                    </toy>`,
            },
        };

        class ToyController extends Component {
            setup() {
                this.class = "toy";
                this.template = xml`${this.props.arch.outerHTML}`;
            }
        }
        ToyController.template = xml`<div t-attf-class="{{class}} {{props.className}}"><t t-call="{{ template }}"/></div>`;
        ToyController.components = { Banner: OnboardingBanner };

        const toyView = {
            type: "toy",
            Controller: ToyController,
        };

        setupViewRegistries();
        viewRegistry.add("toy", toyView);

        target = getFixture();
    });

    QUnit.module("OnboardingBanner");

    QUnit.test("OnboardingBanner fetch the banner when the route is in the session", async (assert) => {
        assert.expect(3);
        patchWithCleanup(session, {
            ...session,
            onboarding_to_display: ["animal"],
        });

        const mockRPC = (route) => {
            if (route === "/onboarding/animal") {
                assert.step(route);
                return { html: `<div class="animalBanner">myBanner</div>` };
            }
        };
        const config = {
            views: [[1, "toy"]],
        };
        const env = await makeTestEnv({ serverData, mockRPC, config });
        const props = {
            resModel: "animal",
            type: "toy",
        };
        await mount(View, target, { env, props });

        assert.verifySteps(["/onboarding/animal"]);
        assert.containsOnce(target, ".animalBanner");
    });

    QUnit.test("OnboardingBanner does not fetch the banner when the route is not in the session", async (assert) => {
        assert.expect(2);

        const mockRPC = (route) => {
            if (route === "/onboarding/animal") {
                assert.step(route);
                return { html: `<div class="animalBanner">myBanner</div>` };
            }
        };
        const config = {
            views: [[1, "toy"]],
        };
        const env = await makeTestEnv({ serverData, mockRPC, config });
        const props = {
            resModel: "animal",
            type: "toy",
        };
        await mount(View, target, { env, props });

        assert.verifySteps([]);
        assert.containsNone(target, ".animalBanner");
    });
});
