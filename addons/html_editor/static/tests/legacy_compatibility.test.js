import { test } from "@odoo/hoot";
import { testEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";

test("data-last-history-steps gets renamed to data-last-history-commits on start", async () => {
    const contentBefore = unformat(`
        <p data-last-history-steps="1">abc</p>
        <div data-last-history-steps="2">
            <p data-last-history-steps="3">def</p>
            <p data-last-history-steps="4">ghi</p>
        </div>
        <p data-last-history-steps="5">jkl</p>
    `);
    const correctedContent = contentBefore.replaceAll("-steps", "-commits");
    await testEditor({
        contentBefore,
        contentBeforeEdit: correctedContent,
        contentAfterEdit: correctedContent,
        contentAfter: correctedContent,
    });
});
