import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("mail_activity_date_format", {
    steps: () => [
        {
            trigger: "button:contains('Activity')",
            run: "click",
        },
        {
            trigger: ".o_selection_badge span:contains('To-Do')",
            run: "click",
        },
        {
            trigger: "div[name='summary'] input",
            run: "edit Go Party",
        },
        {
            trigger: "button:contains('Save')",
            run: "click",
        },
        {
            trigger: ".o-mail-Activity:contains('Go Party')",
            run: "click",
        },
        {
            trigger: ".o-mail-Activity-info i",
            run: () => {
                const icon = document.querySelector(".o-mail-Activity-info i");
                const infoString = icon.dataset.tooltipInfo;
                const { activity } = JSON.parse(infoString);
                if (activity.dateCreateFormatted !== "01/Jan/24 09:00:00 AM") {
                    // Format expected from the server for 9 AM at the first day of 2024 is date_format = "%d/%b/%y", time_format = "%I:%M:%S %p".
                    throw new Error("Incorrect 'Created On'");
                }
                if (activity.dateDeadlineFormatted !== "06/Jan/24") {
                    // Default due date is 5 days after creation date.
                    throw new Error("Incorrect 'Due On'");
                }
            },
        },
    ],
});
