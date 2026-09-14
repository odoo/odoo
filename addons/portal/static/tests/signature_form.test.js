import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { SignatureForm } from "@portal/signature_form/signature_form";
import {
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { Deferred } from "@web/core/utils/concurrency";

const SIGN_URL = "/portal/test/sign";

class DummySignature extends Component {
    static template = xml`<div class="o-dummy-signature"/>`;
    static props = ["*"];
}

function stubSignatureInput() {
    patchWithCleanup(SignatureForm.components, { NameAndSignature: DummySignature });
}

test("successful signature renders the server redirect link", async () => {
    stubSignatureInput();
    onRpc(SIGN_URL, () => ({
        message: "Signed!",
        redirect_url: "/my/doc/42",
        redirect_message: "See your document",
    }));

    const component = await mountWithCleanup(SignatureForm, {
        props: { callUrl: SIGN_URL, defaultName: "Alice" },
    });

    await component.onClickSubmit();
    await animationFrame();

    expect(".alert-success a").toHaveCount(1);
    expect(".alert-success a").toHaveAttribute("href", "/my/doc/42");
    expect(".alert-success a").toHaveText("See your document");
});

test("a failing signature RPC restores the submit button", async () => {
    stubSignatureInput();
    onRpc(SIGN_URL, () => {
        throw new Error("boom");
    });

    const component = await mountWithCleanup(SignatureForm, {
        props: { callUrl: SIGN_URL, defaultName: "Alice" },
    });

    let rejected = false;
    try {
        await component.onClickSubmit();
    } catch {
        rejected = true;
    }
    await animationFrame();

    expect(rejected).toBe(true);
    expect(".o_portal_sign_submit").toHaveCount(1);
    expect(".o_portal_sign_submit i.fa-check").toHaveCount(1);
});

test("concurrent submissions send only one signature", async () => {
    stubSignatureInput();
    const response = new Deferred();
    onRpc(SIGN_URL, () => {
        expect.step("sign");
        return response;
    });
    const component = await mountWithCleanup(SignatureForm, {
        props: { callUrl: SIGN_URL, defaultName: "Alice" },
    });
    const pending = component.onClickSubmit();
    const duplicate = component.onClickSubmit();
    await animationFrame();
    expect(".o_portal_sign_submit").toHaveProperty("disabled", true);
    expect.verifySteps(["sign"]);
    response.resolve({ message: "Signed" });
    await Promise.all([pending, duplicate]);
    await animationFrame();
    expect(".alert-success").toHaveText("Signed");
});

test("signature extraction failure leaves the form retryable", async () => {
    stubSignatureInput();
    const component = await mountWithCleanup(SignatureForm, {
        props: { callUrl: SIGN_URL, defaultName: "Alice" },
    });
    component.signature.getSignatureImage = () => {
        throw new Error("canvas unavailable");
    };
    await expect(component.onClickSubmit()).rejects.toThrow("canvas unavailable");
    await animationFrame();
    expect(".o_portal_sign_submit").toHaveProperty("disabled", false);
    expect(".o_portal_sign_submit i.fa-check").toHaveCount(1);
});

test("a submit-button click sends the entered signature payload", async () => {
    stubSignatureInput();
    onRpc(SIGN_URL, async (request) => {
        const { params } = await request.json();
        expect(params).toEqual({ name: "Alice", signature: "c2lnbmVk" });
        expect.step("signed");
        return { message: "Signed" };
    });
    const component = await mountWithCleanup(SignatureForm, {
        props: { callUrl: SIGN_URL, defaultName: "Alice" },
    });
    component.signature.getSignatureImage = () => "data:image/png;base64,c2lnbmVk";
    component.rootRef.el.querySelector("button").click();
    await animationFrame();
    expect.verifySteps(["signed"]);
    expect(".alert-success").toHaveText("Signed");
});
