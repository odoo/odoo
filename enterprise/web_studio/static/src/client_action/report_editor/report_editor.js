/** @odoo-module */
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

import { useReportEditorModel } from "@web_studio/client_action/report_editor/report_editor_model";
import { ReportEditorWysiwyg } from "@web_studio/client_action/report_editor/report_editor_wysiwyg/report_editor_wysiwyg";
import { ReportEditorXml } from "@web_studio/client_action/report_editor/report_editor_xml/report_editor_xml";

import { getCssFromPaperFormat } from "./utils";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

class ReportEditor extends Component {
    static template = "web_studio.ReportEditor";
    static components = { ReportEditorWysiwyg, ReportEditorXml };
    static props = { ...standardActionServiceProps };

    setup() {
        this.reportEditorModel = useReportEditorModel();
    }

    get paperFormatStyle() {
        const {
            margin_top,
            margin_left,
            margin_right,
            print_page_height,
            print_page_width,
            header_spacing,
        } = this.reportEditorModel.paperFormat;
        const marginTop = Math.max(0, (margin_top || 0) - (header_spacing || 0));
        return getCssFromPaperFormat({
            margin_top: marginTop,
            margin_left,
            margin_right,
            print_page_height,
            print_page_width,
        });
    }
}
registry.category("actions").add("web_studio.report_editor", ReportEditor);
