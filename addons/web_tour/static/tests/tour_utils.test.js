import { describe, expect, test } from "@odoo/hoot";
import { serializeChanges } from "@web_tour/tour_service/tour_utils";

describe.current.tags("desktop");

test("differences between 2 elements", async () => {
    const el = document.createElement("div");
    el.classList.add("brol");
    el.innerHTML = `
        <div>coucou</div>    
        <div>coucou</div>    
        <div>coucou</div>    
        <div><div>blabla</div></div>    
        <div><div class="doku">blabla</div><div class="doka">blabla</div></div>    
        <div><div>blabla</div></div>    
        <div><div>blabla</div></div>    
        <div>coucou</div>    
        <div>coucou</div>    
    `;
    const snapshot = el.cloneNode(true);
    el.querySelector(".doku").textContent = "blibli";
    el.querySelector(".doka").textContent = "bloblo";
    const changes = serializeChanges(snapshot, el);
    expect(changes).toEqual([
        {
            children: [
                {
                    children: [
                        {
                            children: [
                                {
                                    node: "blibli",
                                    text: {
                                        after: "blibli",
                                        before: "blabla",
                                    },
                                },
                            ],
                            node: '<div class="doku"></div>',
                        },
                        {
                            children: [
                                {
                                    node: "bloblo",
                                    text: {
                                        after: "bloblo",
                                        before: "blabla",
                                    },
                                },
                            ],
                            node: '<div class="doka"></div>',
                        },
                    ],
                    node: "<div></div>",
                },
            ],
            node: '<div class="brol"></div>',
        },
    ]);
});
