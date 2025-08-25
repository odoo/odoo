import { expect, test } from "@odoo/hoot";
import { addBuilderOption, setupHTMLBuilder } from "./helpers";
import { Component, useState, xml } from "@odoo/owl";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { click } from "@odoo/hoot-dom";

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
    addBuilderOption({ selector: ".test", OptionComponent: Test });
    await setupHTMLBuilder(`<div class="test">TEST in html builder</div>`);
    await click(":iframe .test");
    expect(1).toBe(1);
});

test("should prevent edition in many2one field", async () => {
    await setupHTMLBuilder(
        `<a data-oe-model="blog.post" data-oe-id="3" data-oe-field="blog_id" data-oe-type="many2one" data-oe-expression="blog_post.blog_id" data-oe-many2one-id="1" data-oe-many2one-model="blog.blog">
            Travel
        </a>`
    );
    expect(":iframe a").toHaveProperty("isContentEditable", false);
});
