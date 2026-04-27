/** @odoo-module **/

function fail(errorMessage) {
    console.error(errorMessage);
}

function assertIn(item, itemList, info) {
    if (!itemList.includes(item)) {
        fail(info + ': "' + item + '" not in "' + itemList + '".');
    }
}
function assert(current, expected, info) {
    if (current !== expected) {
        fail(info + ': "' + current + '" instead of "' + expected + '".');
    }
}

function assertRainbow(present = false) {
    const summaryStep = document.querySelectorAll(".o_tablet_summary");
    const rainbow = document.querySelectorAll(".o_reward_rainbow_man");
    assert(
        Boolean(summaryStep.length && present ? rainbow.length : !rainbow.length),
        true,
        "Rainbow man check"
    );
}

function assertDoneButton(present = false) {
    const doneButton = document.querySelectorAll("button.btn-primary[name=do_finish]");
    assert(Boolean(present ? doneButton.length : !doneButton.length), true, 'mark as done check');
}

function assertQtyToProduce(qty_producing, qty_remaining) {
    let _qty_producing = document.querySelectorAll('input[id="qty_producing_0"]');
    if (_qty_producing.length === 0) {
        _qty_producing = document.querySelectorAll('div[name="qty_producing"]');
        assert(Number(_qty_producing[0].textContent), qty_producing, `wrong quantity done`);
    } else {
        assert(Number(_qty_producing[0].value), qty_producing, `wrong quantity done`);
    }
    assert(_qty_producing.length, 1, `no qty_producing`);

    const _qty_remaining = document.querySelectorAll('div[name="qty_remaining"]');
    assert(_qty_remaining.length, 1, `no qty_remaining`);
    assert(Number(_qty_remaining[0].textContent), qty_remaining, `wrong quantity remaining`);
}

function assertComponent(name, style, qty_done, qty_remaining) {
    assertIn(style, ['readonly', 'editable']);
    const label = document.querySelectorAll('div[name="component_id"] > span');
    assert(label.length, 1, `no field`);
    assert(label[0].textContent, name, `wrong component name`);
    if (style === 'readonly') {
        const _qty_done = document.querySelectorAll('div[name="qty_done"]');
        assert(_qty_done.length, 1, `no qty_done`);
        assert(Number(_qty_done[0].textContent), qty_done, `wrong quantity done`);
    } else {
        const _qty_done = document.querySelectorAll('input[id="qty_done_0"]');
        assert(_qty_done.length, 1, `no qty_done`);
        assert(Number(_qty_done[0].value), qty_done, `wrong quantity done`);
    }
    const _qty_remaining = document.querySelectorAll('div[name="component_remaining_qty"]');
    assert(_qty_remaining.length, 1, `no qty_remaining`);
    assert(Number(_qty_remaining[0].textContent), qty_remaining, `wrong quantity remaining`);
}

function assertCurrentCheck(text) {
    const button = document.querySelectorAll(".o_selected");
    assert(button.length, 1, `no selected check`);
    assert(button[0].textContent, text, `wrong check title`);
}

function assertCheckLength(length) {
    const button = document.querySelectorAll(".o_tablet_step");
    assert(button.length, length, `There should be "${length}" steps`);
}
function assertValidatedCheckLength(length) {
    const marks = document.querySelectorAll(".o_tablet_step_ok");
    assert(marks.length, length, `There should be "${length}" validated steps`);
}

export default {
    assert: assert,
    assertCurrentCheck: assertCurrentCheck,
    assertCheckLength: assertCheckLength,
    assertComponent: assertComponent,
    assertValidatedCheckLength: assertValidatedCheckLength,
    assertQtyToProduce: assertQtyToProduce,
    assertRainbow: assertRainbow,
    assertDoneButton: assertDoneButton,
    fail: fail,
};
