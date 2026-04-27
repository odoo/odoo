/** @odoo-module **/

/**
 * Returns the line for the given index and ensure the line is an HTMLElement (fails otherwise).
 *
 * @param {(HTMLElement|integer)} lineOrIndex either the line itself, either the index to find it
 * @param {string} errorClue
 * @returns {HTMLElement}
 */
export function _getLineOrFail (lineOrIndex, errorClue="No line found") {
    const line = typeof lineOrIndex === "number" ?
        document.querySelectorAll('.o_barcode_line')[lineOrIndex] :
        lineOrIndex;
    if (line instanceof HTMLElement) {
        return line;
    }
    const errorMessage = typeof lineOrIndex === "number" ?
        `${errorClue}: the given index (${lineOrIndex}) doesn't match an existing line` :
        `${errorClue}: the given object isn't a line`;
    fail(errorMessage);
}
/**
 * @param {string} selector
 * @param {Object} description
 * @param {string} [description.barcode] the line's product's barcode
 * @param {Boolean} [description.completed] get only completed line if true
 * @param {Boolean} [description.selected] get only selected line if true
 * @param {string} [description.selector]
 * @returns {string}
 */
export function _prepareSelector(selector, description) {
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
}

export function fail(errorMessage) {
    throw new Error(errorMessage);
}

/**
 * Get and returns exactly one line, fails if multiple lines are found).
 * @param {Object} description @see getLines
 * @returns {HTMLElement}
 */
export function getLine(description = {}) {
    const line = getLines(description);
    if (line.length > 1) {
        fail(`getLine: Multiple lines were found for the selector "${description.selector}" (use 'getLines' instead if its wanted)`);
    } else if (line.length === 0) {
        fail(`getLine: No line was found for the selector "${description.selector}"`);
    }
    return line[0];
}

/**
 * Get and returns all lines matching the given description, fails if no line is found.
 * @param {Object} [description] if no description, will return all the barcode's line
 * @see _prepareSelector for more information about description's keys.
 * @returns {Element[]}
 */
export function getLines(description = {}) {
    const selector = _prepareSelector(":not(.o_sublines) > .o_barcode_line", description);
    const lines = document.querySelectorAll(selector);
    const {index} = description;
    if (index !== undefined) {
        if (typeof index === "number") { // Single index (not an array), returns only one line.
            return [lines[index]];
        }
        const chosenLines = [];
        for (const i of index) {
            chosenLines.push(lines[i]);
        }
        if (chosenLines.length !== index.length) {
            fail(`Expects ${index.length} lines, got ${chosenLines.length}`)
        }
        return chosenLines;
    }
    return Array.from(lines);
}

export function getSubline(description = {}) {
    const subline = getSublines(description);
    if (subline.length > 1) {
        fail(`Multiple sublines were found for the selector "${description.selector}"`);
    }
    return subline[0];
}

export function getSublines(description = {}) {
    const selector = _prepareSelector(".o_sublines .o_barcode_line", description);
    const sublines = document.querySelectorAll(selector);
    if (!sublines.length) {
        fail(`No subline was found for the selector "${selector}"`);
    }
    return sublines;
}

export function triggerKeydown(eventKey, shiftkey = false) {
    document.querySelector('.o_barcode_client_action')
        .dispatchEvent(new window.KeyboardEvent('keydown', {bubbles: true, key: eventKey, shiftKey: shiftkey}));
}

export function assert(current, expected, info) {
    if (current !== expected) {
        fail(`${info}: "${current}" instead of "${expected}".`);
    }
}

/**
 * Checks if a button on the given line is visible or not.
 *
 * @param {HTMLElement|Integer} lineOrIndex the line (or its index) to test its the button visibility
 * @param {string} buttonName could be 'add_quantity', 'remove_unit' or 'set'.
 * @param {boolean} [shouldBeVisible=true]
 */
export function assertButtonIsVisible(lineOrIndex, buttonName, shouldBeVisible = true) {
    const line = _getLineOrFail(lineOrIndex);
    const button = line.querySelector(`.o_line_button.o_${buttonName}`);
    const label = line.querySelector('.o_product_label,.package')?.innerText;
    assert(!!button, shouldBeVisible,
        `${label ? label + " line" : "Line"}'s button "${buttonName}" ${shouldBeVisible ? "should" : "should not"} be visible`);
}

export function assertValidateVisible(expected) {
    const validateButton = document.querySelector('.o_validate_page,.o_apply_page');
    assert(!!validateButton, expected, 'Validate visible');
}

export function assertValidateEnabled(expected) {
    const validateButton = document.querySelector('.o_validate_page,.o_apply_page') || false;
    assert(validateButton && !validateButton.hasAttribute('disabled'), expected, 'Validate enabled');
}

export function assertValidateIsHighlighted(expected) {
    const validateButton = document.querySelector('.o_validate_page,.o_apply_page') || false;
    const isHighlighted = validateButton && validateButton.classList.contains('btn-primary');
    assert(isHighlighted, expected, 'Validate button is highlighted');
}

export function assertLinesCount(expectedCount, description) {
    const currentCount = getLines(description).length;
    assert(currentCount, expectedCount, `Should have ${expectedCount} line(s)`);
}

export function assertScanMessage(expected) {
    const instruction = document.querySelector(`.o_scan_message`);
    const cssClass = instruction.classList[1];
    assert(cssClass, `o_${expected}`, "Not the right message displayed");
}

export function assertSublinesCount(expected) {
    const current = document.querySelectorAll('.o_sublines > .o_barcode_line').length;
    assert(current, expected, `Should have ${expected} subline(s), found ${current}`);
}

export function assertLineDestinationIsNotVisible(lineOrIndex) {
    const line = _getLineOrFail(lineOrIndex);
    const destinationElement = line.querySelector('.o_line_destination_location');
    if (destinationElement) {
        const product = line.querySelector('.o_product_label').innerText;
        fail(`The destination for line of the product ${product} should not be visible, "${destinationElement.innerText}" instead`);
    }
}


/**
 * Checks if the given line is going in the given location. Implies the destination is visible.
 * @param {Element} lineOrIndex
 * @param {string} location
 */
export function assertLineDestinationLocation(lineOrIndex, location) {
    const line = _getLineOrFail(lineOrIndex, "Can't check the line's destination");
    const destinationElement = line.querySelector('.o_line_destination_location');
    const product = line.querySelector('.o_product_label').innerText;
    if (!destinationElement) {
        fail(`The destination (${location}) for line of the product ${product} is not visible`);
    }
    assert(
        destinationElement.innerText, location,
        `The destination for line of product ${product} isn't in the right location`);
}

export function assertLineIsHighlighted(lineOrIndex, expected = true) {
    const line = _getLineOrFail(lineOrIndex, "Can't check if the line is highlighted");
    const errorMessage = `line ${expected ? "should" : "shouldn't"} be highlighted`;
    assert(line.classList.contains('o_highlight'), expected, errorMessage);
}

export function assertLineLocations(lineOrIndex, source = null, destination = null) {
    const line = _getLineOrFail(lineOrIndex, "Can't check line's locations");
    if (source) {
        assertLineSourceLocation(line, source);
    } else {
        assertLineSourceIsNotVisible(line);
    }
    if (destination) {
        assertLineDestinationLocation(line, destination);
    } else {
        assertLineDestinationIsNotVisible(line);
    }
}

export function assertLineProduct(lineOrIndex, productName) {
    const line = _getLineOrFail(lineOrIndex, "Can't check line's product");
    const lineProduct = line.querySelector('.o_product_label').innerText;
    assert(lineProduct, productName, "Not the expected product");
}

/**
 * Checks the package assigned to a line. The expected package can be let
 * empty to check there is no package assigned on the line.
 * @param {(HTMLElement|integer)} lineOrIndex @see _getLineOrFail
 * @param {string} [expectedPackageName]
 */
export function assertLinePackage(lineOrIndex, expectedPackageName) {
    const line = _getLineOrFail(lineOrIndex, "Can't check the line's package");
    const packageEl = line.querySelector("div[name='package'] > .package");
    if (!packageEl) {
        if (expectedPackageName) {
            fail(`There is no package: ${expectedPackageName} expected`);
        }
    } else {
        const linePackageName = packageEl.innerText;
        assert(linePackageName, expectedPackageName, "Not the expected line's package");
    }
}

/**
 * Checks the result package assigned to a line. The expected package can be let
 * empty to check there is no result package assigned on the line.
 * @param {(HTMLElement|integer)} lineOrIndex @see _getLineOrFail
 * @param {string} [expectedPackageName]
 */
export function assertLineResultPackage(lineOrIndex, expectedPackageName = false) {
    const line = _getLineOrFail(lineOrIndex, "Can't check the line's result package");
    const resultPackageEl = line.querySelector(".result-package");
    if (!resultPackageEl) {
        if (expectedPackageName) {
            fail(`There is no result package: ${expectedPackageName} expected`);
        }
    } else {
        const linePackageName = resultPackageEl.innerText;
        assert(linePackageName, expectedPackageName, "Not the expected result package");
    }
}

/**
 * Checks the quantity. It will get the done/counted quantity and will also
 * checks the on the reserved/on hand quantity if there is one.
 * Also, if the unit of measure is displayed, it will check that too.
 *
 * @param {(HTMLElement|integer)} lineOrIndex @see _getLineOrFail
 * @param {string} expectedQuantityWithUOM quantity on the line, formatted as "n (/ N) ( UOM)"
 */
export function assertLineQty(lineOrIndex, expectedQuantityWithUOM) {
    const line = _getLineOrFail(lineOrIndex, "Can't check the line's quantity");
    const elQty = line.querySelector('.o_barcode_scanner_qty');
    const elUOM = line.querySelector('.o_line_uom');
    let qtyText = elQty.innerText;
    let errorMessage = "Something wrong with the quantities";
    if (elUOM) {
        qtyText += " " + elUOM.innerText;
        errorMessage += " or with the Unit of Measure";
    }
    assert(qtyText, expectedQuantityWithUOM, errorMessage);
}

export function assertLineSourceIsNotVisible(lineOrIndex) {
    const line = _getLineOrFail(lineOrIndex);
    const sourceElement = line.parentNode.querySelector('.o_barcode_location_line');
    if (sourceElement) {
        const product = line.querySelector('.o_product_label').innerText;
        fail(`The location for line of the product ${product} should not be visible, "${sourceElement.innerText}" instead`);
    }
}

/**
 * Checks the given lot or serial number is written on the given line.
 * Can also check none is written too.
 *
 * @param {(HTMLElement|integer)} lineOrIndex @see _getLineOrFail
 * @param {string|Boolean} expectedTrackingNumber either the expected lot/serial
 * number (or an empty string if the lot is displayed but empty), either false
 * if the element shouldn't be visible at all.
 */
export function assertLineTrackingNumber(lineOrIndex, expectedTrackingNumber) {
    const line = _getLineOrFail(lineOrIndex);
    const elTrackingNumber = line.querySelector(".o_line_lot_name");
    const product = line.querySelector('.product-label')?.innerText || "";
    if (expectedTrackingNumber === false) {
        assert(
            !!elTrackingNumber, false,
            `No tracking number should be visible on the ${product} line`);
    } else {
        assert(
            !!elTrackingNumber, true,
            `${expectedTrackingNumber} should be visible but there is no tracking number on the ${product} line`);
        assert(
            elTrackingNumber.innerText, expectedTrackingNumber,
            `Not the expected tracking number for the ${product} line`);
    }
}

/**
 * Checks each given lines match the corresponding tracking numbers.
 * The number of lines and tracking numbers has to be equals.
 * @param {HTMLElement[]} lines
 * @param {string[]} trackingNumbers
 */
export function assertLinesTrackingNumbers(lines, trackingNumbers) {
    assert(lines.length, trackingNumbers.length, "Not the same amount of lines and tracking numbers");
    for (const [index, line] of lines.entries()) {
        assertLineTrackingNumber(line, trackingNumbers[index]);
    }
}

/**
 * Checks if the given line is in the given location. Implies the location is visible.
 * @param {Element} lineOrIndex
 * @param {string} location
 */
export function assertLineSourceLocation(lineOrIndex, location) {
    const line = _getLineOrFail(lineOrIndex, "Can't check the line's source");
    const sourceElement = line.parentNode.querySelector('.o_barcode_location_line');
    const product = line.querySelector('.o_product_label').innerText;
    if (!sourceElement) {
        fail(`The source (${location}) for line of the product ${product} is not visible`);
    }
    assert(
        sourceElement.innerText, location,
        `The source for line of product ${product} isn't in the right location`);
}

export function assertFormLocationSrc(expected) {
    const location = document.querySelector('.o_field_widget[name="location_id"] input');
    assert(location.value, expected, 'Wrong source location');
}

export function assertFormLocationDest(expected) {
    const location = document.querySelector('.o_field_widget[name="location_dest_id"] input');
    assert(location.value, expected, 'Wrong destination location');
}

export function assertFormQuantity(expected) {
    const quantityField = document.querySelector(
        '.o_field_widget[name="inventory_quantity"] input, .o_field_widget[name="qty_done"] input');
    assert(quantityField.value, expected, 'Wrong quantity');
}

export function assertErrorMessage(expected) {
    const errorMessage = document.querySelector('.o_notification:last-child .o_notification_content');
    assert(errorMessage.innerText, expected, 'wrong or absent error message');
}

export function assertKanbanRecordsCount(expected) {
    const kanbanRecords = document.querySelectorAll(
        '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)');
    assert(kanbanRecords.length, expected, 'Wrong number of cards');
}

export function assertLineIsFaulty(lineOrIndex, expected = true) {
    const line = _getLineOrFail(lineOrIndex, "Can't check if the line is faulty");
    const errorMessage = `line ${expected ? "should" : "shouldn't"} be faulty`;
    assert(line.classList.contains('o_faulty'), expected, errorMessage);
}
