import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";

setupInteractionWhiteList("website.text_highlight");

describe.current.tags("interaction_dev");

const highlightTemplate = `
    <p>
        Great stories have a <b>personality</b>.
        <span class="o_text_highlight o_translate_inline o_text_highlight_circle_1" style="--text-highlight-width: 2px;">
            <span class="o_text_highlight_item">
                Consider telling a great story that provides personality.
                <svg fill="none" class="o_text_highlight_svg o_content_no_merge position-absolute overflow-visible top-0 start-0 w-100 h-100 pe-none">
                    <path stroke-width="var(--text-highlight-width)" stroke="var(--text-highlight-color)" stroke-linecap="round" d="M 142.36111111111111,18.18181818181818 C 372.7272727272727,19.047619047619047 430.5,18.18181818181818 419.42999999999995,8.620689655172415C 410, 1.36986301369863 290.5740609496811,0 205,0 S -2,1.36986301369863 -2,9.09090909090909S 96.69811320754717,20 301.4705882352941,20.8" class="o_text_highlight_path_circle_1"></path>
                </svg>
            </span>
        </span>
         Writing a story with personality for potential clients will assist with making a relationship connection. This shows up in small quirks like word choices or phrases. Write from your point of view, not from someone else's experience.
    </p>
`;

test("text_highlight is started when there is an element #wrapwrap", async () => {
    const { core } = await startInteractions(highlightTemplate);
    expect(core.interactions).toHaveLength(1);
});

test("[resize] update the number of highlight items when necessary", async () => {
    const { el } = await startInteractions(highlightTemplate);
    el.querySelector("div").style.width = "1000px";

    // Ensure the update is finished
    await animationFrame();
    await animationFrame();
    const numberOfItems1 = el.querySelectorAll(".o_text_highlight_item").length;

    el.querySelector("div").style.width = "200px";

    // Ensure the update is finished
    await animationFrame();
    await animationFrame();
    const numberOfItems2 = el.querySelectorAll(".o_text_highlight_item").length;

    expect(numberOfItems1 < numberOfItems2).toBe(true);
});
