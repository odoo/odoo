import { Component, t, useProps } from "@odoo/owl";

export class FsReportDebugPopover extends Component {
    static template = "account_fs_report.FsReportDebugPopover";
    props = useProps({
        close: t.function(),
        expressionsDetail: t.array(),
        onClose: t.function().optional(),
    });
}
