import { animationFrame, expect, test } from "@odoo/hoot";
import { queryOne, waitFor } from "@odoo/hoot-dom";
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { switchToEditMode } from "../../helpers";

setupInteractionWhiteList("website.page_breadcrumb");

test("Breadcrumb adjusts its position on header resize", async () => {
    const { core } = await startInteractions(
        `<div id="wrapwrap" contenteditable="false" class="odoo-editor-editable">
            <header id="top" data-anchor="true" data-name="Header" class="o_header_standard o_top_fixed_element">
                    Header Content
            </header>
            <main class="o_breadcrumb_overlay">
                <div class="o_page_breadcrumb" data-name="Breadcrumb">
                    Breadcrumb Content
                </div>
            </main>
        </div>`
    );
    await switchToEditMode(core);
    await animationFrame();
    await waitFor("div#wrapwrap > header");
    await waitFor("div.o_page_breadcrumb");
    const header = queryOne("header#top");
    const breadcrumb = queryOne(".o_page_breadcrumb");
    await animationFrame();
    expect(breadcrumb.getBoundingClientRect().top).toBe(header.getBoundingClientRect().height);
    header.style.height = "50px";
    await animationFrame();
    expect(breadcrumb.style.top).toBe("50px");
    header.classList.add("d-none");
    await animationFrame();
    expect(breadcrumb.style.top).toBe("0px");
});
