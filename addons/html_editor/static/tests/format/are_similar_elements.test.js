import { test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";

test("should consider elements with same classes and styles in different orders as similar", async () => {
    await testEditor({
        contentBefore: `<span class="first second" style="color: red; color2: blue">hello</span><span class="second first" style="color2: blue; color: red">world</span>`,
        contentBeforeEdit: `<div class="o-paragraph"><span class="first second" style="color: red; color2: blue">helloworld</span></div>`,
    });
});
test("should consider different when the number of styles are different", async () => {
    await testEditor({
        contentBefore: `<span class="first second" style="color: red; color2: blue">hello</span><span class="second first" style="color2: blue;">world</span>`,
        contentBeforeEdit: `<div class="o-paragraph"><span class="first second" style="color: red; color2: blue">hello</span><span class="second first" style="color2: blue;">world</span></div>`,
    });
});
test("should consider different when the number of classes are different", async () => {
    await testEditor({
        contentBefore: `<span class="first">hello</span><span class="second first">world</span>`,
        contentBeforeEdit: `<div class="o-paragraph"><span class="first">hello</span><span class="second first">world</span></div>`,
    });
});
test("should consider different when classes are different", async () => {
    await testEditor({
        contentBefore: `<span class="first">hello</span><span class="second">world</span>`,
        contentBeforeEdit: `<div class="o-paragraph"><span class="first">hello</span><span class="second">world</span></div>`,
    });
});
test("should consider different when styles are different", async () => {
    await testEditor({
        contentBefore: `<span class="first" style="color: red;">hello</span><span class="second" style="color: blue;">world</span>`,
        contentBeforeEdit: `<div class="o-paragraph"><span class="first" style="color: red;">hello</span><span class="second" style="color: blue;">world</span></div>`,
    });
});
