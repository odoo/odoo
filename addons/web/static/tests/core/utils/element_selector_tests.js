/** @odoo-module **/

import { ElementSelector } from "@web/core/utils/element_selector";
import { getFixture } from "@web/../tests/helpers/utils";

let target;

QUnit.module("utils", () => {
    QUnit.module("Element Selector", {
        beforeEach: () => {
            target = getFixture();
        },
    });

    QUnit.test("get element", (assert) => {
        const toChecks = [
            [".item:first-child", "document.querySelectorAll(`.item:first-child`);"],
            [".item:contains(hello)", "document.querySelectorAll(`.item`).containsText(`hello`);"],
            [
                ".item:contains(hello MON LOULOU)",
                "document.querySelectorAll(`.item`).containsText(`hello MON LOULOU`);",
            ],
            [
                ".item:contains('hello MON LOULOU')",
                "document.querySelectorAll(`.item`).containsText(`hello MON LOULOU`);",
            ],
            [
                '.item:contains("hello MON LOULOU")',
                "document.querySelectorAll(`.item`).containsText(`hello MON LOULOU`);",
            ],
            [
                '.item:contains("hello MON LOULOU") .item:contains(mon coco)',
                "document.querySelectorAll(`.item`).containsText(`hello MON LOULOU`).querySelectorAll(`.item`).containsText(`mon coco`);",
            ],
            [
                "document.querySelectorAll(`.item`).containsText(`hello MON LOULOU`);",
                "document.querySelectorAll(`.item`).containsText(`hello MON LOULOU`);",
            ],
        ];
        assert.expect(toChecks.length);
        for (const toCheck of toChecks) {
            assert.strictEqual(new ElementSelector(toCheck[0]).toText, toCheck[1]);
        }
    });

    QUnit.test("ElementSelector.contains()", (assert) => {
        const container = document.createElement("div");
        container.classList.add("hello");
        target.appendChild(container);
        for (let i = 0; i < 10; i++) {
            const blabla = document.createElement("div");
            blabla.classList.add("blabla");
            blabla.textContent = "blabla";
            container.appendChild(blabla);
            for (let i = 0; i < 10; i++) {
                const blibli = document.createElement("div");
                blibli.classList.add("blibli");
                blibli.textContent = "blibli";
                blabla.appendChild(blibli);
            }
        }
        assert.strictEqual(new ElementSelector(".hello").contains(".blabla"), 10);
        assert.strictEqual(new ElementSelector(".hello").contains(".blibli"), 100);
        assert.strictEqual(
            new ElementSelector(".hello").contains(
                document.querySelectorAll("div.blibli").containsText("blibli")
            ),
            100
        );
    });

    QUnit.test("assert.containsX", (assert) => {
        for (let i = 0; i < 10; i++) {
            const container = document.createElement("div");
            container.classList.add("hello");
            container.textContent = "Coucou !!!";
            target.appendChild(container);
        }
        const container = document.createElement("div");
        container.classList.add("brol");
        target.appendChild(container);
        assert.containsN(target, ".hello", 10);
        assert.containsN(target, document.querySelectorAll("div").containsText("Coucou !!!"), 10);
        assert.containsN(target, "div.hello:contains(Coucou !!!)", 10);
        assert.containsN(target, ".hello:contains(Coucou !!!)", 10);
        assert.containsNone(target, ".blibla");
        assert.containsOnce(target, ".brol");
        assert.containsOnce(document.querySelectorAll(".hello")[0], ".brol");
    });
});
