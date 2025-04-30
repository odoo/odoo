import { negateStep } from "@point_of_sale/../tests/generic_helpers/utils";

export function checkCashMoveShown(amount) {
    return {
        content: `Check has cash move with amount ${amount}`,
        trigger: `.cash-move-list .cash-move-row .cash-move-amount:contains(${amount})`,
    };
}
export function deleteCashMove(amount) {
    return [
        {
            content: `Delete cash move with amount ${amount}`,
            trigger: `.cash-move-list .cash-move-row:contains(${amount}) .delete-row .btn`,
            run: "click",
        },
        negateStep(checkCashMoveShown(amount)),
    ];
}
export function checkNumberOfRows(number) {
    return {
        content: "check number of cash moves",
        trigger: ".cash-move-list .cash-move-row",
        run: () => {
            const cashMoveRows = document.querySelectorAll(".cash-move-list .cash-move-row").length;
            if (cashMoveRows !== number) {
                throw new Error(`Expected ${number} cash moves, found ${cashMoveRows}`);
            }
        },
    };
}
