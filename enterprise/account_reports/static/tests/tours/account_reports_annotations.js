/** @odoo-module **/

import { Asserts } from "./asserts";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("account_reports_annotations", {
    url: "/odoo/action-account_reports.action_account_report_bs",
    steps: () => [
        //--------------------------------------------------------------------------------------------------------------
        // Annotations
        //--------------------------------------------------------------------------------------------------------------
        // Test the initial status of annotations - There are 2 annotations to display
        {
            content: "Initial annotations",
            trigger: ".o_content",
            run: () => {
                Asserts.DOMContainsNone(".annotations");
            },
        },
        {
            content: "Unfold first line",
            trigger: "tr:nth-child(4) td:first()",
            run: "click",
        },
        {
            content: "Unfold second line",
            trigger: "tr:nth-child(7) td:first()",
            run: "click",
        },
        {
            content: "Unfold third line",
            trigger: "tr:nth-child(10) td:first()",
            run: "click",
        },
        {
            content: "Extra Trigger step",
            trigger: "tr:nth-child(12):not(.d-none) .name:contains('101404')",
        },
        {
            content: "Check there are two lines annotated initially",
            trigger: ".o_content",
            run: () => {
                const annotations = document.querySelectorAll(".btn_annotation .fa-commenting");

                // Check the number of annotated lines
                Asserts.isEqual(annotations.length, 2);

                // Check the annotations buttons are on the right lines
                Asserts.isTrue(
                    annotations[0] ===
                        document.querySelector("tr:nth-child(5)").querySelector(".fa-commenting")
                );
                Asserts.isTrue(
                    annotations[1] ===
                        document.querySelector("tr:nth-child(12)").querySelector(".fa-commenting")
                );
            },
        },
        // Test that we can add a new annotation
        {
            content: "Click to show caret option",
            trigger: "tr:nth-child(8) .dropdown-toggle",
            run: "click",
        },
        {
            content: "Caret option is displayed",
            trigger: "tr:nth-child(8)",
            run: () => {
                Asserts.hasClass("tr:nth-child(8) .o-dropdown", "show");
            },
        },
        {
            content: "Click on annotate",
            trigger: ".o-dropdown--menu .dropdown-item:last-of-type:contains('Annotate')",
            run: "click",
        },
        {
            content: "Add text to annotate",
            trigger: "textarea",
            run: "edit Annotation 121000",
        },
        {
            content: "Submit annotation by blurring",
            trigger: "textarea",
            run: function () {
                const annotation = this.anchor;
                annotation.dispatchEvent(new InputEvent("input"));
                annotation.dispatchEvent(new Event("change"));
            },
        },
        {
            content: "Wait for annotation created",
            trigger: "tr:nth-child(8) .btn_annotation .fa-commenting",
        },
        {
            content: "Close annotation",
            trigger: ".o_content",
            run: "click",
        },
        {
            content: "Check there are now three lines annotated",
            trigger: ".o_content",
            run: () => {
                const annotations = document.querySelectorAll(".btn_annotation .fa-commenting");

                // Check the number of annotated lines
                Asserts.isEqual(annotations.length, 3);

                // Check the annotations buttons are on the right lines
                Asserts.isTrue(
                    annotations[0] ===
                        document.querySelector("tr:nth-child(5)").querySelector(".fa-commenting")
                );
                Asserts.isTrue(
                    annotations[1] ===
                        document.querySelector("tr:nth-child(8)").querySelector(".fa-commenting")
                );
                Asserts.isTrue(
                    annotations[2] ===
                        document.querySelector("tr:nth-child(12)").querySelector(".fa-commenting")
                );
            },
        },
        // Test that we can edit an annotation
        {
            content: "Open second annotated line annotation popover",
            trigger: "tr:nth-child(8) .btn_annotation",
            run: "click",
        },
        {
            content: "Annotate contains previous text value",
            trigger: "textarea",
            run: () => {
                Asserts.isEqual(document.querySelector("textarea").value, "Annotation 121000");
            },
        },
        {
            content: "Add text to annotate",
            trigger: "textarea",
            run: "edit Annotation 121000 edited",
        },
        {
            content: "Annotation is edited",
            trigger: "tr:nth-child(8) .btn_annotation",
            run: () => {
                Asserts.isEqual(
                    document.querySelector(".annotation_popover_autoresize_textarea").value,
                    "Annotation 121000 edited"
                );
            },
        },
        // Test that we can delete an annotation by clicking the trash icon
        {
            content: "Click on trash can",
            trigger: ".btn_annotation_delete",
            run: "click",
        },
        {
            content: "Check there are now only two lines annotated",
            trigger: "tr:nth-child(8):not(:has(.fa-commenting))",
            run: () => {
                const annotations = document.querySelectorAll(".btn_annotation .fa-commenting");

                // Check the number of annotated lines
                Asserts.isEqual(annotations.length, 2);

                // Check the annotations buttons are on the right lines
                Asserts.isTrue(
                    annotations[0] ===
                        document.querySelector("tr:nth-child(5)").querySelector(".fa-commenting")
                );
                Asserts.isTrue(
                    annotations[1] ===
                        document.querySelector("tr:nth-child(12)").querySelector(".fa-commenting")
                );
            },
        },
        // Test that we can add an annotation by clicking on the "New" button inside the popover
        {
            content: "Open an annotated line annotation popover",
            trigger: "tr:nth-child(12) .btn_annotation",
            run: "click",
        },
        {
            content: "Click on the 'New' button",
            trigger: ".annotation_popover_line .oe_link",
            run: "click",
        },
        {
            content: "Add text to annotate",
            trigger: "textarea:last()",
            run: "edit Annotation 101404 bis",
        },
        {
            content: "Submit annotation by blurring",
            trigger: "textarea:last()",
            run: function () {
                const annotation = this.anchor;
                annotation.dispatchEvent(new InputEvent("input"));
                annotation.dispatchEvent(new Event("change"));
            },
        },
        // Check the current state of the annotations
        {
            content: "Check there are two annotated lines to end the test",
            trigger: ".o_content",
            run: () => {
                const annotations = document.querySelectorAll(".btn_annotation .fa-commenting");

                // Check there is only one annotated line
                Asserts.isEqual(annotations.length, 2);

                // Check the annotation buttons are on the right lines
                Asserts.isTrue(
                    annotations[0] ===
                        document.querySelector("tr:nth-child(5)").querySelector(".fa-commenting")
                );
                Asserts.isTrue(
                    annotations[1] ===
                        document.querySelector("tr:nth-child(12)").querySelector(".fa-commenting")
                );
            },
        },
        //--------------------------------------------------------------------------------------------------------------
        // Annotations dates
        //--------------------------------------------------------------------------------------------------------------
        {
            content:
                "Remove first annotation to only have one annotation on line 12 (required setup step)",
            trigger: ".annotation_popover tr:nth-child(2) .btn_annotation_delete",
            run: "click",
        },
        {
            content: "Verify that we still have one element",
            trigger: ".annotation_popover tr:nth-child(3):contains('Add a line')",
        },
        {
            content: "Modify the date of an annotation to a further period",
            trigger: ".annotation_popover tr:nth-child(2) input",
            run: "edit 01/01/2100",
        },
        {
            content: "Modify the date of an annotation to a further period",
            trigger: ".annotation_popover tr:nth-child(2) input",
            run: function () {
                // Since the t-on-change of the input is not triggered by the run: "edit" action,
                // we need to dispatch the event manually requiring a function.
                const input = this.anchor;
                input.dispatchEvent(new InputEvent("input"));
                input.dispatchEvent(new Event("change", { bubbles: true }));
            },
        },
        {
            content: "Check that there is no annotation anymore on line 12",
            trigger: "tr:nth-child(12):not(:has(.fa-commenting))",
        },
        {
            content: "change date filter",
            trigger: "#filter_date button",
            run: "click",
        },
        {
            content: "Open specific date button",
            trigger: ".dropdown-menu div.dropdown-item",
            run: "click",
        },
        {
            content: "Go to 15 January 2100",
            trigger: ".o_datetime_input",
            run: "edit 01/15/2100",
        },
        {
            content: "Apply filter by closing the dropdown",
            trigger: "#filter_date .btn:first()",
            run: "click",
        },
        {
            content: "wait refresh",
            trigger: `#filter_date button:not(:contains(${new Date().getFullYear()}))`,
        },
        {
            content: "Check there is one annotation on line 12",
            trigger: "tr:nth-child(12):has(.fa-commenting)",
            run: () => {
                const annotations = document.querySelectorAll(".btn_annotation .fa-commenting");

                // Check there is only one annotated line
                Asserts.isEqual(annotations.length, 1);

                // Check the annotation buttons are on the right lines
                Asserts.isTrue(
                    annotations[0] ===
                        document.querySelector("tr:nth-child(12)").querySelector(".fa-commenting")
                );
            }
        },
    ]
});
