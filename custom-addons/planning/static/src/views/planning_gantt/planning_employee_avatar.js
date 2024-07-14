/* @odoo-module */

import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { useEffect, useRef } from "@odoo/owl";

export class PlanningEmployeeAvatar extends Avatar {
    setup() {
        super.setup();
        const displayNameRef = useRef("displayName");
        useEffect(
            (displayNameEl) => {
                // Mute the last content between parenthesis in Gantt title column
                const text = displayNameEl.textContent;
                const jobTitleRegexp = /^(.*)(\(.*\))$/;
                const jobTitleMatch = text.match(jobTitleRegexp);
                if (jobTitleMatch) {
                    const textMuted = document.createElement("span");
                    textMuted.className = "text-muted text-truncate";
                    textMuted.replaceChildren(jobTitleMatch[2]);
                    displayNameEl.replaceChildren(jobTitleMatch[1], textMuted);
                }
            },
            () => [displayNameRef.el]
        );
    }
}
PlanningEmployeeAvatar.template = "planning.PlanningEmployeeAvatar";
