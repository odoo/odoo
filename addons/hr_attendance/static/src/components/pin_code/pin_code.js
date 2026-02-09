import { useState } from "@web/owl2/utils";
import { Component, onWillStart, onWillDestroy } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { range } from "@web/core/utils/numbers";

export class KioskPinCode extends Component {
    static template = "hr_attendance.KioskPinConfirm";
    static props = {
        employeeData: { type: Object },
        onClickBack: { type: Function },
        onPinConfirm: { type: Function },
    };

    setup() {
        this.padButtons = [
            ...range(1, 10).map((i) => [i]),
            ["C", "btn-warning"],
            [0],
            ["OK", "btn-primary"],
        ];
        this.state = useState({
            codePin: "",
        });
        this.lockPad = false;
        this.checkedIn = this.props.employeeData.attendance_state === 'checked_in';

        const onKeyDown = async (ev) => {
            const allowedKeys = { Delete: "C", Enter: "OK", Backspace: null };
            Object.assign(allowedKeys, range(10)); // { from '0': 0 ... to '9': 9 }
            const key = ev.key;

            if (!Object.keys(allowedKeys).includes(key)) {
                return;
            }

            ev.preventDefault();
            ev.stopPropagation();

            if (allowedKeys[key] !== null) {
                await this.onClickPadButton(allowedKeys[key]);
            }
            else {
                this.state.codePin = this.state.codePin.substring(0, this.state.codePin.length - 1);
            }
        }
        browser.addEventListener('keydown', onKeyDown);
        onWillStart(() => browser.addEventListener('keydown', onKeyDown))
        onWillDestroy(() => browser.removeEventListener('keydown', onKeyDown));
    }

    async onClickPadButton(value) {
        if (this.lockPad) {
            return;
        }
        if (value === "C") {
            this.state.codePin = "";
        } else if (value === "OK") {
            this.lockPad = true;
            await this.props.onPinConfirm(this.props.employeeData.id, this.state.codePin)
            this.state.codePin = "";
            this.lockPad = false;
        } else {
            this.state.codePin += value;
        }
    }
}
