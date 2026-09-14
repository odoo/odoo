/** @odoo-module native */
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";
import { Dropdown, DropdownItem } from "@web/components/dropdown";
import { _t } from "@web/core/translation";
import { rpc } from "@web/core/network";
import { Pager } from "@web/components/pager";
import { MEDIAS_BREAKPOINTS, SIZES } from "@web/ui/viewport";

export class KioskManualSelection extends Component {
    static template = "hr_attendance.public_kiosk_manual_selection";
    static components = {
        Dropdown,
        DropdownItem,
        Pager,
    };
    static props = {
        displayBackButton: { type: Boolean },
        token: { type: String },
        departments: { type: Array },
        onSelectEmployee: { type: Function },
        onClickBack: { type: Function },
    };

    setup() {
        let limit = this.calculateLimit();
        this.state = useState({
            employeesData: {
                count: 0,
                records: [],
            },
            offset: 0,
            limit: limit,
            searchInput: "",
            searchDomain: [],
            departmentDomain: [],
        });
        this.departmentName = _t("All departments");
        onWillStart(async () => {
            await this._fetchEmployeeData();
        });
        this._onResize = async () => {
            this.state.limit = this.calculateLimit();
            await this._fetchEmployeeData();
        };
        onMounted(() => browser.addEventListener("resize", this._onResize));
        onWillUnmount(() => browser.removeEventListener("resize", this._onResize));
    }

    calculateLimit() {
        let employeeCardPerLine = 1;
        let fontSizeMultiplication = 1;
        let searchBarHeight = 0;
        if (screen.width <= MEDIAS_BREAKPOINTS[SIZES.SM].maxWidth) {
            searchBarHeight += 38;
        } else if (screen.width <= MEDIAS_BREAKPOINTS[SIZES.MD].maxWidth) {
            employeeCardPerLine = 2;
        } else if (screen.width <= MEDIAS_BREAKPOINTS[SIZES.LG].maxWidth) {
            fontSizeMultiplication *= 1.25;
            employeeCardPerLine = 2;
        } else if (screen.width <= MEDIAS_BREAKPOINTS[SIZES.XL].maxWidth) {
            fontSizeMultiplication *= 1.25;
            if (screen.width < 1400) {
                employeeCardPerLine = 3;
            } else {
                employeeCardPerLine = 4;
            }
        } else {
            employeeCardPerLine = 4;
            if (screen.width <= 2560) {
                fontSizeMultiplication *= 1.35;
            } else {
                fontSizeMultiplication *= 2;
            }
        }
        let employeeCardHeight = 150 * fontSizeMultiplication;
        searchBarHeight += 62 * fontSizeMultiplication;
        let availableScreen = screen.height - searchBarHeight;
        return Math.trunc(availableScreen / employeeCardHeight) * employeeCardPerLine;
    }

    async _onPagerChanged({ offset, limit }) {
        this.state.offset = offset;
        this.state.limit = limit;
        await this._fetchEmployeeData();
    }

    async _fetchEmployeeData() {
        const domain = Domain.and([
            this.state.departmentDomain,
            this.state.searchDomain,
        ]).toList();
        const results = await rpc("/hr_attendance/employees_infos", {
            token: this.props.token,
            limit: this.state.limit,
            offset: this.state.offset,
            domain: domain,
        });
        // The route answers `{status: "error"}` when the token no longer opens
        // this company's kiosk. Assigning its absent `records` straight into
        // state left the grid iterating `undefined`.
        this.state.employeesData.records = results?.records ?? [];
        this.state.employeesData.count = results?.length ?? 0;
    }

    async onDepartmentClick(departmentId = false) {
        if (this.env.isSmall) {
            if (departmentId) {
                const selectedDepartment = this.props.departments.find(
                    (department) => department.id === departmentId,
                );
                this.departmentName = selectedDepartment.name;
            } else {
                this.departmentName = _t("All departments");
            }
        }
        if (departmentId) {
            this.state.departmentDomain = [["department_id", "=", departmentId]];
        } else {
            this.state.departmentDomain = [];
        }
        this.state.offset = 0;
        await this._fetchEmployeeData();
    }

    async onSearchInput(ev) {
        const searchInput = ev.target.value;
        if (searchInput.length) {
            this.state.searchDomain = [["name", "ilike", searchInput]];
        } else {
            this.state.searchDomain = [];
        }
        this.state.offset = 0;
        await this._fetchEmployeeData();
    }
}
