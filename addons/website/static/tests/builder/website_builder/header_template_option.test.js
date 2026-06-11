import { expect, test } from "@odoo/hoot";
import { isHeaderBgBlurAvailable } from "@website/builder/plugins/options/header/header_template_option";

const makeHtmlStyle = (vars) => ({ getPropertyValue: (prop) => vars[prop] || "" });

const expectBlur = (vars, overrides) =>
    expect(isHeaderBgBlurAvailable(makeHtmlStyle(vars), overrides));

test("should check if header bg blur is available correctly", () => {
    expectBlur({ "--menu-custom": "rgb(255, 0, 0)" }).toBe(false);
    expectBlur({ "--menu-custom": "#ff0000ff" }).toBe(false);

    expectBlur({ "--menu-custom": "rgba(255, 0, 0, 0.5)" }).toBe(true);
    expectBlur({ "--menu-custom": "#ff000080" }).toBe(true);
    expectBlur({
        "--menu-custom": "rgba(0, 0, 0, 0)",
        "--menu-gradient": "linear-gradient(rgba(255,0,0,0.5), blue)",
    }).toBe(true);
    expectBlur({
        "--menu-custom": "#ff0000",
        "--menu-gradient": "linear-gradient(rgba(0,0,0,0.5), rgba(255,255,255,1))",
    }).toBe(true);

    expectBlur({
        "--menu-custom": "#ff0000",
        "--menu-gradient": "linear-gradient(#ff0000, #0000ff)",
    }).toBe(false);
    expectBlur({
        "--menu-custom": "#ff0000",
        "--menu-gradient": "linear-gradient(#ff000080, #0000ffff)",
    }).toBe(true);
    expectBlur({
        "--menu-custom": "#ff0000",
        "--menu-gradient": "linear-gradient(#ff0000ff, #0000ffff)",
    }).toBe(false);

    // Overriding style should take precedence over html style values.
    expectBlur({ "--menu-custom": "rgba(0, 0, 0, 0.5)" }, { "menu-custom": "rgb(255, 0, 0)" }).toBe(
        false
    );
    expectBlur({ "--menu-custom": "rgb(255, 0, 0)" }, { "menu-custom": "rgba(0, 0, 0, 0.5)" }).toBe(
        true
    );
});
