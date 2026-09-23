import { expect, onError, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    getService,
    makeMockEnv,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { CartNotificationContainer } from "@website_sale/js/notification/notification_service";

class Boom extends Component {
    static props = ["*"];
    static template = xml`<div t-out="this.props.missing.length"/>`;
}

class TestCartContainer extends CartNotificationContainer {
    static serviceName = "notification";
    static components = { ...CartNotificationContainer.components, Notification: Boom };
}

test("a throwing cart toast does not take the whole container down with it", async () => {
    expect.errors(1);
    onError(() => expect.step("contained"));

    await makeMockEnv();
    await mountWithCleanup(TestCartContainer, { noMainContainer: true });
    expect(".pe-none").toHaveCount(1);

    getService("notification").add("boom");
    await animationFrame();
    await animationFrame();

    expect.verifySteps(["contained"]);
    expect.verifyErrors([/Cannot read properties of undefined/]);
    expect(".pe-none").toHaveCount(1, {
        message: "the container survived the toast that threw",
    });
});
