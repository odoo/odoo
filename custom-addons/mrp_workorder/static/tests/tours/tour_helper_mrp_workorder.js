/** @odoo-module **/

import { TourError } from "@web_tour/tour_service/tour_utils";

function fail(errorMessage) {
    throw new TourError(errorMessage);
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
    const $summaryStep = $('.o_tablet_summary');
    const $rainbow = $('.o_reward_rainbow_man');
    assert(Boolean($summaryStep.length && present ? $rainbow.length : !$rainbow.length), true, 'Rainbow man check');
}

function assertDoneButton(present = false) {
    const $doneButton = $('button.btn-primary[name=do_finish]');
    assert(Boolean(present ? $doneButton.length : !$doneButton.length), true, 'mark as done check');
}

function assertQtyToProduce(qty_producing, qty_remaining) {
    let $qty_producing = $('input[id="qty_producing_0"]');
    if ($qty_producing.length === 0) {
        $qty_producing = $('div[name="qty_producing"]');
        assert(Number($qty_producing[0].textContent), qty_producing, `wrong quantity done`);
    } else {
        assert(Number($qty_producing[0].value), qty_producing, `wrong quantity done`);
    }
    assert($qty_producing.length, 1, `no qty_producing`);

    const $qty_remaining = $('div[name="qty_remaining"]');
    assert($qty_remaining.length, 1, `no qty_remaining`);
    assert(Number($qty_remaining[0].textContent), qty_remaining, `wrong quantity remaining`);
}

function assertComponent(name, style, qty_done, qty_remaining) {
    assertIn(style, ['readonly', 'editable']);
    const $label = $('div[name="component_id"] > span');
    assert($label.length, 1, `no field`);
    assert($label[0].textContent, name, `wrong component name`);
    if (style === 'readonly') {
        const $qty_done = $('div[name="qty_done"]');
        assert($qty_done.length, 1, `no qty_done`);
        assert(Number($qty_done[0].textContent), qty_done, `wrong quantity done`);
    } else {
        const $qty_done = $('input[id="qty_done_0"]');
        assert($qty_done.length, 1, `no qty_done`);
        assert(Number($qty_done[0].value), qty_done, `wrong quantity done`);
    }
    const $qty_remaining = $('div[name="component_remaining_qty"]');
    assert($qty_remaining.length, 1, `no qty_remaining`);
    assert(Number($qty_remaining[0].textContent), qty_remaining, `wrong quantity remaining`);
}

function assertCurrentCheck(text) {
    const $button = $('.o_selected');
    assert($button.length, 1, `no selected check`);
    assert($button[0].textContent, text, `wrong check title`);
}

function assertCheckLength(length) {
    const button = $('.o_tablet_step');
    assert(button.length, length, `There should be "${length}" steps`);
}
function assertValidatedCheckLength(length) {
    const marks = $('.o_tablet_step_ok');
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
