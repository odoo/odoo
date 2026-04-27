import { UrlField } from "@web/views/fields/url/url_field";

export class HrContractSalaryUrlField extends UrlField {
    static template = "hr_contract_salary.UrlField";

    async saveOfferAndRedirect(ev) {
        ev.preventDefault()
        await this.props.record.save();
        window.open(this.props.text || this.props.record.data[this.props.name] || '').focus()
    }
}