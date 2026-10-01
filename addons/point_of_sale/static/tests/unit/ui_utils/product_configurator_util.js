import { animationFrame } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

export async function pickColor(name) {
    await contains(
        `.modal .configurator_color[data-color="${name}"], .modal label[title="${name}"]`
    ).click();
    await animationFrame();
}

export async function pickRadio(name) {
    const labels = [
        ...document.querySelectorAll(
            ".modal .attribute-name-cell label, .modal .configurator_radio label"
        ),
    ];
    const label = labels.find((l) => l.textContent.includes(name));
    if (label) {
        await contains(label).click();
    } else {
        const input = [...document.querySelectorAll(".modal .attribute-name-cell input")].find(
            (i) => i.closest(".attribute-name-cell")?.textContent.includes(name)
        );
        if (input) {
            await contains(input).click();
        }
    }
    await animationFrame();
}

export async function pickMulti(name) {
    const label = [...document.querySelectorAll('.modal label[for^="multi-"]')].find((l) =>
        l.textContent.includes(name)
    );
    if (label) {
        await contains(label).click();
        await animationFrame();
    }
}

export async function pickSelect(name) {
    const selects = document.querySelectorAll(".modal select.configurator_select");
    for (const select of selects) {
        const option = [...select.options].find((opt) => opt.textContent.trim() === name);
        if (option) {
            select.value = option.value;
            select.dispatchEvent(new Event("change", { bubbles: true }));
            await animationFrame();
            return;
        }
    }
}

export async function fillCustomAttribute(value) {
    await contains(".modal input.custom_value").edit(value);
    await animationFrame();
}

export async function confirmConfigurator() {
    await contains(".modal .btn-primary").click();
    await animationFrame();
}

export function isColorSelected(name) {
    const el = document.querySelector(
        `.modal .configurator_color.active[data-color="${name}"], .modal label.configurator_color.active[title="${name}"]`
    );
    return el !== null;
}

export function isRadioSelected(name) {
    const cells = document.querySelectorAll(
        ".modal .attribute-name-cell, .modal .configurator_radio .attribute-name-cell"
    );
    for (const cell of cells) {
        if (cell.textContent.includes(name)) {
            const input = cell.querySelector("input:checked");
            if (input) {
                return true;
            }
        }
    }
    return false;
}

export function isMultiSelected(name) {
    const label = [
        ...document.querySelectorAll(
            '.modal label[for^="multi-"].active, .modal label.form-check-label.active'
        ),
    ].find((l) => l.textContent.includes(name));
    return label !== null;
}

export function getSelectValue() {
    const select = document.querySelector(".modal select.configurator_select");
    return select ? select.options[select.selectedIndex]?.textContent.trim() : null;
}

export function getCustomAttributeValue() {
    const input = document.querySelector(".modal input.custom_value");
    return input ? input.value : null;
}
