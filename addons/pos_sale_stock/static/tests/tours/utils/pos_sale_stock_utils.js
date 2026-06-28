import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";

export function selectedOrderLinesHasLots(productName, lots) {
    const getSerialStep = (index, serialNumber) => ({
        content: `check lot${index} is linked`,
        trigger: `.info-list li:contains(${serialNumber})`,
    });
    const lotSteps = lots.reduce((acc, serial, i) => acc.concat(getSerialStep(i, serial)), []);
    return [...ProductScreen.selectedOrderlineHas(productName), ...lotSteps];
}
