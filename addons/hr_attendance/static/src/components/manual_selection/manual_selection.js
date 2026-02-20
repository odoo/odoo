import { Component, useState, onWillStart } from "@odoo/owl";

import { Domain } from "@web/core/domain";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { Pager } from "@web/core/pager/pager";
import { MEDIAS_BREAKPOINTS, SIZES } from "@web/core/ui/ui_service";
import { useService } from "@web/core/utils/hooks";
import { AttendanceVideoStream } from "@hr_attendance/components/attendance_video_stream/attendance_video_stream";

export class KioskManualSelection extends Component {
    static template = "hr_attendance.public_kiosk_manual_selection";
    static components = {
        Dropdown,
        DropdownItem,
        Pager,
        AttendanceVideoStream,
    };
    static props = {
        displayBackButton: { type: Boolean },
        token: { type: String },
        departments: { type: Array },
        onSelectEmployee: { type: Function },
        onClickBack: { type: Function },
        captureCheckInPicture: { type: Boolean },
    };

    setup() {
        this.orm = useService("orm");
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
        })
    }

    calculateLimit() {
        // This function calculates the maximum number of employee cards that can fit on the screen based on his size,
        // font size, and the number of cards per row.
        let employeeCardPerLine = 1;
        let fontSizeMultiplication = 1;
        let searchBarHeight = 0;
        // for small screen the searchbar is higher

        const width = window.innerWidth;
        const kioskContainer = document.querySelector(".o_hr_attendance_kiosk_mode");
        const kioskContainerHeight = kioskContainer
            ? kioskContainer.clientHeight
            : window.innerHeight;

        if (width <= MEDIAS_BREAKPOINTS[SIZES.SM].maxWidth) {
            searchBarHeight += 38;
        } else if (width <= MEDIAS_BREAKPOINTS[SIZES.MD].maxWidth) {
            employeeCardPerLine = 2;
        } else if (width <= MEDIAS_BREAKPOINTS[SIZES.LG].maxWidth) {
            fontSizeMultiplication *= 1.25;
            employeeCardPerLine = 2;
        } else if (width <= MEDIAS_BREAKPOINTS[SIZES.XL].maxWidth) {
            fontSizeMultiplication *= 1.25;
            if (width < 1400) {
                //grid breakpoint xxl
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

        const employeeCardHeight = 150 * fontSizeMultiplication;
        searchBarHeight += 62 * fontSizeMultiplication;
        let availableScreen = kioskContainerHeight - searchBarHeight;

        if (this.props.captureCheckInPicture) {
            const topBarElement = document.querySelector(".o_attendance_top_bar");
            const topBarElementHeight = topBarElement ? topBarElement.offsetHeight : 0;
            availableScreen -= topBarElementHeight;
        }

        return Math.trunc(availableScreen / employeeCardHeight) * employeeCardPerLine;
    }

    async _onPagerChanged({ offset, limit }) {
        this.state.offset = offset;
        this.state.limit = limit;
        await this._fetchEmployeeData();
    }

    async _fetchEmployeeData() {
        const domain = Domain.and([this.state.departmentDomain, this.state.searchDomain]).toList();
        const results = await rpc("/hr_attendance/employees_infos", {
            token: this.props.token,
            limit: this.state.limit,
            offset: this.state.offset,
            domain: domain,
        });
        this.state.employeesData.records = results.records;
        this.state.employeesData.count = results.length;
    }

    async onDepartmentClick(departmentId = false){
        if (this.env.isSmall) {
            if (departmentId){
                const selectedDepartment = this.props.departments.find((department) => department.id === departmentId);
                this.departmentName = selectedDepartment.name;
            } else {
                this.departmentName = _t("All departments");
            }
        }
        if (departmentId){
            this.state.departmentDomain = [['department_id', '=', departmentId]];
        } else {
            this.state.departmentDomain = [];
        }
        this.state.offset = 0;
        await this._fetchEmployeeData();
    }

    async onSearchInput(ev) {
        const searchInput = ev.target.value;
        if (searchInput.length){
            this.state.searchDomain = [['name', 'ilike', searchInput]];
        }else{
            this.state.searchDomain = [];
        }
        this.state.offset = 0;
        await this._fetchEmployeeData();
    }
}
