/* @odoo-module */

export const stepUtils = {
    enterPIN(code) {
        const steps = [];
        for (const c of code) {
            steps.push({
                trigger: `.popup-numpad button:contains(${c})`,
                run: "click",
            });
        }
        steps.push({
            trigger: `.popup-input:contains('${"".padEnd(code.length, "•")}')`,
        });
        steps.push({
            trigger: "footer .btn-primary",
            run: "click",
        });
        return steps;
    },
};
