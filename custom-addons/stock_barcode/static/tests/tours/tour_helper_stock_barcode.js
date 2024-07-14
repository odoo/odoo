/** @odoo-module **/

import { TourError } from "@web_tour/tour_service/tour_utils";


const helper = {};
export default helper;

/**
 * Returns the line for the given index and ensure the line is an HTMLElement (fails otherwise).
 *
 * @param {(HTMLElement|integer)} lineOrIndex either the line itself, either the index to find it
 * @param {string} errorClue
 * @returns {HTMLElement}
 */
helper._getLineOrFail = (lineOrIndex, errorClue="No line found") => {
    const line = typeof lineOrIndex === "number" ?
        document.querySelectorAll('.o_barcode_line')[lineOrIndex] :
        lineOrIndex;
    if (line instanceof HTMLElement) {
        return line;
    }
    const errorMessage = typeof lineOrIndex === "number" ?
        `${errorClue}: the given index (${lineOrIndex}) doesn't match an existing line` :
        `${errorClue}: the given object isn't a line`;
    helper.fail(errorMessage);
};
/**
 * @param {Object} description
 * @param {string} [description.barcode] the line's product's barcode
 * @param {Boolean} [description.completed] get only completed line if true
 * @param {Boolean} [description.selected] get only selected line if true
 * @returns {string}
 */
helper._prepareSelector = (selector, description) => {
    const { barcode, selected, completed } = description;
    if (selected !== undefined) {
        selector += selected ? ".o_selected" : ":not(.o_selected)";
    }
    if (completed !== undefined) {
        selector += completed ? ".o_line_completed" : ":not(.o_line_completed)";
    }
    selector += barcode ? `[data-barcode="${barcode}"]`: "";
    description.selector = selector;
    return selector;
};

helper.fail = (errorMessage) => {
    throw new TourError(errorMessage);
};

/**
 * Get and returns exactly one line, helper.fails if multiple lines are found).
 * @param {Object} description @see getLines
 * @returns {HTMLElement}
 */
helper.getLine = (description={}) => {
    const line = helper.getLines(description);
    if(line.length > 1) {
        helper.fail(`getLine: Multiple lines were found for the selector "${description.selector}" (use 'getLines' instead if its wanted)`);
    } else if (line.length === 0) {
        helper.fail(`getLine: No line was found for the selector "${description.selector}"`);
    }
    return line[0];
};

/**
 * Get and returns all lines matching the given description, helper.fails if no line is found.
 * @param {Object} [description] if no description, will return all the barcode's line
 * @see _prepareSelector for more information about description's keys.
 * @returns {HTMLElement[]}
 */
helper.getLines = (description={}) => {
    const selector = helper._prepareSelector(".o_barcode_lines > .o_barcode_line", description);
    const lines = document.querySelectorAll(selector);
    const { index } = description;
    if (index !== undefined) {
        if (typeof index === "number") { // Single index (not an array), returns only one line.
            return [lines[index]];
        };
        const chosenLines = [];
        for (const i of index) {
            chosenLines.push(lines[i]);
        }
        if (chosenLines.length !== index.length) {
            helper.fail(`Expects ${index.length} lines, got ${chosenLines.length}`)
        }
        return chosenLines;
    }
    return lines;
};

helper.getSubline = (description={}) => {
    const subline = helper.getSublines(description);
    if(subline.length > 1) {
        helper.fail(`Multiple sublines were found for the selector "${description.selector}"`);
    }
    return subline[0];
};

helper.getSublines = (description={}) => {
    const selector = helper._prepareSelector(".o_sublines .o_barcode_line", description);
    const sublines = document.querySelectorAll(selector);
    if (!sublines.length) {
        helper.fail(`No subline was found for the selector "${selector}"`);
    }
    return sublines;
};

helper.triggerKeydown = (eventKey, shiftkey=false) => {
    document.querySelector('.o_barcode_client_action')
        .dispatchEvent(new window.KeyboardEvent('keydown', { bubbles: true, key: eventKey, shiftKey: shiftkey}));
};

helper.assert = (current, expected, info) => {
    if (current !== expected) {
        helper.fail(info + ': "' + current + '" instead of "' + expected + '".');
    }
};

/**
 * Checks if a button on the given line is visible or not.
 *
 * @param {HTMLElement|Integer} lineOrIndex the line (or its index) to test its the button visibility
 * @param {string} buttonName could be 'add_quantity', 'remove_unit' or 'set'.
 * @param {boolean} [isVisible=true]
 */
helper.assertButtonShouldBeVisible = (lineOrIndex, buttonName, shouldBeVisible=true) => {
    const line = helper._getLineOrFail(lineOrIndex);
    const button = line.querySelector(`.o_line_button.o_${buttonName}`);
    helper.assert(Boolean(button), shouldBeVisible,
        `Line's button "${buttonName}" ${shouldBeVisible ? "should" : "shouldn't"} be visible`);
};

/**
 * Checks if both "Add unit" and "Add reserved remaining quantity" buttons are
 * displayed or not on the given line.
 *
 * @param {integer} lineIndex
 * @param {boolean} isVisible
 */
helper.assertLineButtonsAreVisible = (lineOrIndex, isVisible, cssSelector='.o_line_button') => {
    const line = helper._getLineOrFail(lineOrIndex);
    const buttonAddQty = line.querySelectorAll(cssSelector);
    const message = `Buttons must be ${(isVisible ? 'visible' : 'hidden')}`;
    helper.assert(buttonAddQty.length > 0, isVisible, message);
};

helper.assertValidateVisible = (expected) => {
    const validateButton = document.querySelector('.o_validate_page,.o_apply_page');
    helper.assert(Boolean(validateButton), expected, 'Validate visible');
};

helper.assertValidateEnabled = (expected) => {
    const validateButton = document.querySelector('.o_validate_page,.o_apply_page') || false;
    helper.assert(validateButton && !validateButton.hasAttribute('disabled'), expected, 'Validate enabled');
};

helper.assertValidateIsHighlighted = (expected) => {
    const validateButton = document.querySelector('.o_validate_page,.o_apply_page') || false;
    const isHighlighted = validateButton && validateButton.classList.contains('btn-success');
    helper.assert(isHighlighted, expected, 'Validate button is highlighted');
};

helper.assertLinesCount = (expectedCount, description) => {
    const currentCount = helper.getLines(description).length;
    helper.assert(currentCount, expectedCount, `Should have ${expectedCount} line(s)`);
};

helper.assertScanMessage = (expected) => {
    const instruction = document.querySelector(`.o_scan_message`);
    const cssClass = instruction.classList[1];
    helper.assert(cssClass, `o_${expected}`, "Not the right message displayed");
};

helper.assertSublinesCount = (expected) => {
    const current = document.querySelectorAll('.o_sublines > .o_barcode_line').length;
    helper.assert(current, expected, `Should have ${expected} subline(s), found ${current}`);
};

helper.assertLineDestinationIsNotVisible = (lineOrIndex) => {
    const line = helper._getLineOrFail(lineOrIndex);
    const destinationElement = line.querySelector('.o_line_destination_location');
    if (destinationElement) {
        const product = line.querySelector('.product-label').innerText;
        helper.fail(`The destination for line of the product ${product} should not be visible, "${destinationElement.innerText}" instead`);
    }
};

/**
 * Checks if the given line is going in the given location. Implies the destination is visible.
 * @param {Element} line
 * @param {string} location
 */
helper.assertLineDestinationLocation = (lineOrIndex, location) => {
    const line = helper._getLineOrFail(lineOrIndex, "Can't check the line's destination");
    const destinationElement = line.querySelector('.o_line_destination_location');
    const product = line.querySelector('.product-label').innerText;
    if (!destinationElement) {
        helper.fail(`The destination (${location}) for line of the product ${product} is not visible`);
    }
    helper.assert(
        destinationElement.innerText, location,
        `The destination for line of product ${product} isn't in the right location`);
};

helper.assertLineIsHighlighted =  (lineOrIndex, expected=true) => {
    const line = helper._getLineOrFail(lineOrIndex, "Can't check if the line is highlighted");
    const errorMessage = `line ${expected ? "should" : "shouldn't"} be highlighted`;
    helper.assert(line.classList.contains('o_highlight'), expected, errorMessage);
};

helper.assertLineLocations = (lineOrIndex, source=false, destination=false) => {
    const line = helper._getLineOrFail(lineOrIndex, "Can't check line's locations");
    if (source) {
        helper.assertLineSourceLocation(line, source);
    } else {
        helper.assertLineSourceIsNotVisible(line);
    }
    if (destination) {
        helper.assertLineDestinationLocation(line, destination);
    } else {
        helper.assertLineDestinationIsNotVisible(line);
    }
};

helper.assertLineProduct = (lineOrIndex, productName) => {
    const line = helper._getLineOrFail(lineOrIndex, "Can't check line's product");
    const lineProduct = line.querySelector('.product-label').innerText;
    helper.assert(lineProduct, productName, "Not the expected product");
};

/**
 * Checks the quantity. It will get the done/counted quantity and will also
 * checks the on the reserved/on hand quantity if there is one.
 * Also, if the unit of measure is displayed, it will check that too.
 *
 * @param {(HTMLElement|integer)} lineOrIndex @see _getLineOrFail
 * @param {string} expectedQty quantity on the line, formatted as "n (/ N) ( UOM)"
 */
helper.assertLineQty = (lineOrIndex, expectedQuantityWithUOM) => {
    const line = helper._getLineOrFail(lineOrIndex, "Can't check the line's quantity");
    const elQty = line.querySelector('.qty-done');
    const elUOM = line.querySelector('.o_line_uom');
    const elReserved = elQty.nextElementSibling;
    let qtyText = elQty.innerText + (elReserved ? " " + elReserved.innerText : "");
    let errorMessage = "Something wrong with the quantities";
    if (elUOM) {
        qtyText += " " + elUOM.innerText;
        errorMessage += " or with the Unit of Measure";
    }
    helper.assert(qtyText, expectedQuantityWithUOM, errorMessage);
};

helper.assertLineSourceIsNotVisible = (lineOrIndex) => {
    const line = helper._getLineOrFail(lineOrIndex);
    const sourceElement = line.querySelector('.o_line_source_location');
    if (sourceElement) {
        const product = line.querySelector('.product-label').innerText;
        helper.fail(`The location for line of the product ${product} should not be visible, "${sourceElement.innerText}" instead`);
    }
};

/**
 * Checks each given lines match the corresponding tracking numbers.
 * The number of lines and tracking numbers has to be equals.
 * @param {HTMLElement[]} lines
 * @param {string[]} trackingNumbers
 */
helper.assertLinesTrackingNumbers = (lines, trackingNumbers) => {
    helper.assert(lines.length, trackingNumbers.length, "Not the same amount of lines and tracking numbers");
    for (const [index, line] of lines.entries()) {
        const lineTrackingNumber = line.querySelector(".o_line_lot_name").innerText;
        const expectedTrackingNumber = trackingNumbers[index];
        helper.assert(lineTrackingNumber, expectedTrackingNumber, "Not the expected tracking number");
    }
};

/**
 * Checks if the given line is in the given location. Implies the location is visible.
 * @param {Element} line
 * @param {string} location
 */
helper.assertLineSourceLocation = (lineOrIndex, location) => {
    const line = helper._getLineOrFail(lineOrIndex, "Can't check the line's source");
    const sourceElement = line.querySelector('.o_line_source_location');
    const product = line.querySelector('.product-label').innerText;
    if (!sourceElement) {
        helper.fail(`The source (${location}) for line of the product ${product} is not visible`);
    }
    helper.assert(
        sourceElement.innerText, location,
        `The source for line of product ${product} isn't in the right location`);
};

helper.assertFormLocationSrc = (expected) => {
    const location = document.querySelector('.o_field_widget[name="location_id"] input');
    helper.assert(location.value, expected, 'Wrong source location');
};

helper.assertFormLocationDest = (expected) => {
    const location = document.querySelector('.o_field_widget[name="location_dest_id"] input');
    helper.assert(location.value, expected, 'Wrong destination location');
};

helper.assertFormQuantity = (expected) => {
    const quantityField = document.querySelector(
        '.o_field_widget[name="inventory_quantity"] input, .o_field_widget[name="qty_done"] input');
    helper.assert(quantityField.value, expected, 'Wrong quantity');
};

helper.assertErrorMessage = (expected) => {
    const errorMessage = document.querySelector('.o_notification:last-child .o_notification_content');
    helper.assert(errorMessage.innerText, expected, 'wrong or absent error message');
};

helper.assertKanbanRecordsCount = (expected) => {
    const kanbanRecords = document.querySelectorAll(
        '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)');
    helper.assert(kanbanRecords.length, expected, 'Wrong number of cards');
};

helper.assertLineIsFaulty =  (lineOrIndex, expected=true) => {
    const line = helper._getLineOrFail(lineOrIndex, "Can't check if the line is faulty");
    const errorMessage = `line ${expected ? "should" : "shouldn't"} be faulty`;
    helper.assert(line.classList.contains('o_faulty'), expected, errorMessage);
};
