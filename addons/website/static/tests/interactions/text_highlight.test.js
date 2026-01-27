import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, queryAll, queryFirst } from "@odoo/hoot-dom";

setupInteractionWhiteList("website.text_highlight");

describe.current.tags("interaction_dev");

const highlightTemplate = `
    <p>
        Great stories have a <b>personality</b>.
        <span class="o_text_highlight o_text_highlight_circle_1" style="--text-highlight-width: 2px;">
            Consider telling a great story that provides personality.
            <svg fill="none" class="o_text_highlight_svg o_content_no_merge position-absolute overflow-visible pe-none">
                <path stroke-width="var(--text-highlight-width)" stroke="var(--text-highlight-color)" stroke-linecap="round" d="M 142.36111111111111,18.18181818181818 C 372.7272727272727,19.047619047619047 430.5,18.18181818181818 419.42999999999995,8.620689655172415C 410, 1.36986301369863 290.5740609496811,0 205,0 S -2,1.36986301369863 -2,9.09090909090909S 96.69811320754717,20 301.4705882352941,20.8" class="o_text_highlight_path_circle_1"></path>
            </svg>
        </span>
         Writing a story with personality for potential clients will assist with making a relationship connection. This shows up in small quirks like word choices or phrases. Write from your point of view, not from someone else's experience.
    </p>
`;

test("text_highlight is started when there is an element #wrapwrap", async () => {
    const { core } = await startInteractions(highlightTemplate);
    expect(core.interactions).toHaveLength(1);
});

test("[resize] update the number of highlight items when necessary", async () => {
    await startInteractions(highlightTemplate);
    queryFirst("div").style.width = "1000px";

    // Ensure the update is finished
    await animationFrame();
    await animationFrame();
    const numberOfItems1 = queryAll(".o_text_highlight svg").length;

    queryFirst("div").style.width = "200px";

    // Ensure the update is finished
    await animationFrame();
    await animationFrame();
    const numberOfItems2 = queryAll(".o_text_highlight svg").length;

    expect(numberOfItems1).toBeLessThan(numberOfItems2);
});

test("[rtl] SVG positionned inside highlighted text", async () => {
    const relativePosition = (element, relativeElement) => {
        const e = element.getBoundingClientRect();
        const r = relativeElement.getBoundingClientRect();
        const position = [];
        if (Math.round(e.left) < Math.round(r.left)) {
            position.push("beforeLeft");
        }
        if (Math.round(e.top) < Math.round(r.top)) {
            position.push("beforeTop");
        }
        if (Math.round(e.right) > Math.round(r.right)) {
            position.push("afterRight");
        }
        if (Math.round(e.bottom) > Math.round(r.bottom)) {
            position.push("afterBottom");
        }
        return position.join() || "inside";
    }
    await startInteractions(`
      <p style="direction: rtl">
        اَلْعَرَﺐِﻳَّ<span class="o_text_highlight o_text_highlight_circle_1" style="--text-highlight-width: 2px;">ةُ<br>اَ</span>لْعَرَبِيَّةُ
        <br>
        hello worl<span class="o_text_highlight o_text_highlight_circle_1" style="--text-highlight-width: 2px;">d<br>h</span>ello world
      </p>
    `);
    // Ensure the update is finished
    await animationFrame();
    expect(".o_text_highlight svg").toHaveCount(4);
    const containers = queryAll(".o_text_highlight");
    const items = queryAll(".o_text_highlight svg");
    // all SVG are positionned inside the container
    expect(relativePosition(items[0], containers[0])).toBe("inside");
    expect(relativePosition(items[1], containers[0])).toBe("inside");
    expect(relativePosition(items[2], containers[1])).toBe("inside");
    expect(relativePosition(items[3], containers[1])).toBe("inside");
    // in RTL with RTL content, hightlight of previous line is top left
    expect(relativePosition(items[1], items[0])).toBe("afterRight,afterBottom");
    // in RTL with LTR content, highlight of previous line is top right
    expect(relativePosition(items[3], items[2])).toBe("beforeLeft,afterBottom");
});
