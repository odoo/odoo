import { afterEach, beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, tick } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { defineStyle } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList(["website_forum.website_forum_share", "website.share"]);
describe.current.tags("interaction_dev");


beforeEach(() => defineStyle(`* { transition: none !important; }`));
afterEach(() => {
    document.body.querySelector("#oe_social_share_modal")?.remove();
});

test("sessionStorage social_share is cleared after start", async () => {
    sessionStorage.setItem("social_share", JSON.stringify({
        targetType: "answer",
    }));
    expect(sessionStorage.getItem("social_share")).toEqual('{"targetType":"answer"}');
    await startInteractions(`
         <div id="wrapwrap" class="website_forum">
            <div class="o_wforum_question" data-state="active"></div>
         </div>
    `);
    expect(sessionStorage.getItem("social_share")).toBe(null);
});


describe("target types", () => {
    test("target type answer shows modal with website_forum.social_message_answer", async () => {
        sessionStorage.setItem("social_share", JSON.stringify({
            targetType: "answer",
        }));
        const { core, el } = await startInteractions(`
             <div id="wrapwrap" class="website_forum">
                <div class="o_wforum_question" data-state="active"></div>
             </div>
        `);
        expect(core.interactions).toHaveLength(2);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(el.ownerDocument.body.querySelector(".modal")).toBeVisible();
        expect(el.ownerDocument.body.querySelector(".modal p")).toHaveText(/^By sharing you answer, you will get additional/);
    });

    test("target type question shows modal with website_forum.social_message_question", async () => {
        sessionStorage.setItem("social_share", JSON.stringify({
            targetType: "question",
        }));
        const { core, el } = await startInteractions(`
             <div id="wrapwrap" class="website_forum">
                <div class="o_wforum_question" data-state="active"></div>
             </div>
        `);
        expect(core.interactions).toHaveLength(2);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(el.ownerDocument.body.querySelector(".modal")).toBeVisible();
        expect(el.ownerDocument.body.querySelector(".modal p")).toHaveText(/^On average,/);
    });

    test("target type default shows modal with website_forum.social_message_default", async () => {
        sessionStorage.setItem("social_share", JSON.stringify({
            targetType: "default",
        }));
        const { core, el } = await startInteractions(`
             <div id="wrapwrap" class="website_forum">
                <div class="o_wforum_question" data-state="active"></div>
             </div>
        `);
        expect(core.interactions).toHaveLength(2);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(el.ownerDocument.body.querySelector(".modal")).toBeVisible();
        expect(el.ownerDocument.body.querySelector(".modal p")).toHaveText(/^Share this content to increase your chances/);
    });
});

describe("forum share state", () => {
    test("pending state doesn't show .s_share", async () => {
        sessionStorage.setItem("social_share", JSON.stringify({
            targetType: "answer",
        }));
        const { core, el } = await startInteractions(`
             <div id="wrapwrap" class="website_forum">
                <div class="o_wforum_question" data-state="pending"></div>
             </div>
        `);
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(el.ownerDocument.body.querySelector(".modal")).toBeVisible();
        expect(el.ownerDocument.body.querySelector(".modal .s_share")).toBe(null);
    });

    test("active state shows .s_share", async () => {
        sessionStorage.setItem("social_share", JSON.stringify({
            targetType: "answer",
        }));
        const { core, el } = await startInteractions(`
             <div id="wrapwrap" class="website_forum">
                <div class="o_wforum_question" data-state="active"></div>
             </div>
        `);
        expect(core.interactions).toHaveLength(2);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(el.ownerDocument.body.querySelector(".modal")).toBeVisible();
        expect(el.ownerDocument.body.querySelector(".modal .s_share")).toBeVisible();
    });
});
