import { registry } from "@web/core/registry";
import { selectionField, SelectionField } from "@web/views/fields/selection/selection_field";
import { onMounted } from "@odoo/owl";

const fieldRegistry = registry.category("fields");

class SelectionFitOption extends SelectionField {
    static template = "hr_holidays.SelectionFitOption"

    setup() {
        super.setup()
        onMounted(async() => {
            this.select = document.getElementById(this.props.id)
            this.autoWidth(20)
        })
    }

    autoWidth(offset = 0) {
        if (this.select == null) return
        let fakeSelect = document.createElement("select")
        let fakeOption = document.createElement("option")
        let fakeText = document.createTextNode(this.select.selectedOptions[0].label)
        fakeSelect.style.width = "auto"
        fakeSelect.style.minWidth = "0"
        fakeOption.appendChild(fakeText)
        fakeSelect.appendChild(fakeOption)
        this.select.parentElement.appendChild(fakeSelect)
        this.select.parentElement.style.width = fakeSelect.offsetWidth + offset + "px"
        this.select.parentElement.removeChild(fakeSelect)
    }
}

const selectionFitOption = { ...selectionField, component: SelectionFitOption };

fieldRegistry.add("selection_fit_option", selectionFitOption);
