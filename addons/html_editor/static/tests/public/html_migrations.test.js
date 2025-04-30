import { HtmlUpgradeManager } from "@html_editor/html_migrations/html_upgrade_manager";
import { afterEach, beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { setupMigrateFunctions } from "@html_editor/../tests/public/html_migrations_test_utils";

setupInteractionWhiteList("html_editor.html_migrations");

describe.current.tags("interaction_dev");

describe("Public HTML migration only run once per interaction", () => {
    beforeEach(() => {
        registry
            .category("html_editor_upgrade")
            .category("1.1")
            .add(
                "test_public_html_migrations",
                "@html_editor/../tests/public/html_migrations_test_utils"
            );
        patchWithCleanup(HtmlUpgradeManager.prototype, {
            processForUpgrade() {
                expect.step("html upgrade");
                return super.processForUpgrade(...arguments);
            },
        });
    });
    afterEach(() => {
        registry
            .category("html_editor_upgrade")
            .category("1.1")
            .remove("test_public_html_migrations");
    });
    test("HTML migration is not executed if interactions are restarted", async () => {
        setupMigrateFunctions([
            (container) => {
                container.querySelector("div").replaceChildren(document.createTextNode("after"));
            },
        ]);
        const { core } = await startInteractions(`<div data-oe-version="1.0">before</div>`);
        expect.verifySteps(["html upgrade"]);
        expect(queryOne("#wrapwrap")).toHaveInnerHTML(`<div>after</div>`);
        core.stopInteractions();
        await core.startInteractions();
        expect.verifySteps([]);
        expect(queryOne("#wrapwrap")).toHaveInnerHTML(`<div>after</div>`);
    });
    test("HTML migration is not attempted again and has no consequence on the DOM if it failed", async () => {
        setupMigrateFunctions([
            () => {
                expect.step("html upgrade attempt");
                throw new Error("failed html migration");
            },
        ]);
        const { core } = await startInteractions(`<div data-oe-version="1.0">before</div>`);
        expect.verifySteps(["html upgrade", "html upgrade attempt"]);
        expect(queryOne("#wrapwrap")).toHaveInnerHTML(`<div>before</div>`);
        core.stopInteractions();
        await core.startInteractions();
        expect.verifySteps([]);
        expect(queryOne("#wrapwrap")).toHaveInnerHTML(`<div>before</div>`);
    });
});

describe("public html migration to editor version 1.1", () => {
    test("replace excalidraw embedded component by a link", async () => {
        await startInteractions(
            `<div><p data-oe-version="1.0">Hello World</p><div data-embedded="draw" data-embedded-props='{"source": "https://excalidraw.com"}'/></div>`
        );
        await animationFrame();
        expect(queryOne("#wrapwrap")).toHaveInnerHTML(
            `<div><p>Hello World</p><p><a href="https://excalidraw.com">https://excalidraw.com</a></p></div>`
        );
    });
});
