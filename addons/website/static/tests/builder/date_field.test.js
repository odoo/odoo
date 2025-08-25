import { expect, test } from "@odoo/hoot";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { Component, useState, xml } from "@odoo/owl";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { click } from "@odoo/hoot-dom";

defineWebsiteModels();

class Test extends Component {
    static template = xml`
        <SelectMenu
            choices="getChoices()"
        >
        </SelectMenu>
    `;
    static components = { SelectMenu };
    setup() {
        this.state = useState({ choices: [] });
    }
    getChoices() {
        // setTimeout(() => {
        //     this.state.choices = [
        //         { value: "a", label: "A" },
        //         { value: "x", label: "X" },
        //     ];
        // }, 3000);
        return this.state.choices;
    }
}

test("autofocus in select menu", async () => {
    addOption({ selector: ".test", Component: Test });
    await setupWebsiteBuilder(`<div class="test">TEST in website</div>`);
    await click(":iframe .test");
    expect(1).toBe(1);
});

test("should not allow edition of date and datetime fields", async () => {
    await setupWebsiteBuilder(
        `<time data-oe-model="blog.post" data-oe-id="3" data-oe-field="post_date" data-oe-type="datetime" data-oe-expression="blog_post.post_date" data-oe-original="2025-07-30 09:54:36" data-oe-original-with-format="07/30/2025 09:54:36" data-oe-original-tz="Europe/Brussels">
            Jul 30, 2025
        </time>`
    );
    expect(":iframe time").toHaveProperty("isContentEditable", false);
});
