/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SectionAndNoteFieldOne2Many } from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";

const { useSubEnv } = owl;

export class SaleSectionAndNoteFieldOne2Many extends  SectionAndNoteFieldOne2Many {
    setup() {
        super.setup();
       
        const getList = () => this.list;
        useSubEnv({
            get x2mList() { return getList() }
        });
    }
}

registry.category("fields").add("sale_section_and_note_one2many", SaleSectionAndNoteFieldOne2Many);
