import { Component, onWillStart, useState, onWillDestroy } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

export class KioskPinCode extends Component {
    static template = "hr_attendance.KioskPinConfirm";
    static props = {
        employeeData: { type: Object },
        onClickBack: { type: Function },
        onPinConfirm: { type: Function },
    };

    setup() {
        this.padButtons = [
            ...Array.from({ length: 9 }, (_, i) => [i + 1]), // [[1], ..., [9]]
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
            const allowedKeys = [...Array(10).keys()].reduce((acc, value) => { // { from '0': '0' ... to '9': '9' }
                acc[value] = value;
                return acc;
            }, {
                'Delete': 'C',
                'Enter': 'OK',
                'Backspace': null,
            });
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
