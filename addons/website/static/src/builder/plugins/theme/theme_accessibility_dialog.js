import { Component, onMounted, onWillUnmount, proxy, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

const WCAG_URL = "https://www.w3.org/WAI/WCAG22/Understanding/";

const CHECKS = {
    "theme-paragraph": {
        description: _t(
            "Paragraph theme values cannot fail WCAG on their own. Compliance depends on the page remaining usable when readers resize and override text spacing."
        ),
        links: [
            ["1.4.4", _t("Resize Text"), "resize-text"],
            ["1.4.12", _t("Text Spacing"), "text-spacing"],
        ],
    },
    "theme-headings": {
        description: _t(
            "WCAG does not require the authored heading line height to be at least 1.5. The page must remain usable when a reader overrides line height to 1.5 and applies the other text-spacing values. Heading structure must also be checked in the page content."
        ),
        links: [
            ["1.3.1", _t("Info and Relationships"), "info-and-relationships"],
            ["1.4.4", _t("Resize Text"), "resize-text"],
            ["1.4.12", _t("Text Spacing"), "text-spacing"],
        ],
    },
    "theme-link": {
        description: _t(
            "When links are distinguished only by color, they need 3:1 contrast with surrounding text and a non-color cue on hover or focus. Always underlining links avoids relying on color alone."
        ),
        links: [["1.4.1", _t("Use of Color"), "use-of-color"]],
    },
    "theme-shadow": {
        description: _t(
            "A shadow has no standalone WCAG requirement. If it is the only visual boundary of a control, that control must still remain identifiable with sufficient non-text contrast."
        ),
        links: [["1.4.11", _t("Non-text Contrast"), "non-text-contrast"]],
    },
    "theme-advanced": {
        description: _t(
            "These global settings cannot be assessed from their theme values alone. Custom code and changes to the header must be audited in the resulting pages."
        ),
        links: [
            ["2.4.5", _t("Multiple Ways"), "multiple-ways"],
            ["3.2.3", _t("Consistent Navigation"), "consistent-navigation"],
        ],
    },
};

const createProbe = (document) => {
    const probe = document.createElement("div");
    probe.className = "position-fixed invisible pe-none";
    probe.style.cssText = "inset: 0 auto auto 0; width: 320px; z-index: -1;";
    document.body.appendChild(probe);
    return probe;
};

const analyzeTargets = (document, kind) => {
    const probe = createProbe(document);
    const definitions =
        kind === "button"
            ? [
                  [_t("Small button"), "button", "btn btn-primary btn-sm"],
                  [_t("Regular button"), "button", "btn btn-primary"],
                  [_t("Large button"), "button", "btn btn-primary btn-lg"],
              ]
            : [
                  [_t("Small input"), "input", "form-control form-control-sm"],
                  [_t("Regular input"), "input", "form-control"],
                  [_t("Large input"), "input", "form-control form-control-lg"],
              ];
    const issues = [];
    const roundUp = (value) => Math.ceil(Math.max(0, value) * 10) / 10;
    for (const [label, tagName, className] of definitions) {
        const element = document.createElement(tagName);
        element.className = className;
        if (tagName === "button") {
            element.type = "button";
            element.textContent = "A";
        } else {
            element.type = "text";
            element.value = "Input";
        }
        probe.appendChild(element);
        const { width, height } = element.getBoundingClientRect();
        if (width < 24 || height < 24) {
            const style = document.defaultView.getComputedStyle(element);
            const fontSize = parseFloat(style.fontSize);
            const currentPaddingY =
                (parseFloat(style.paddingTop) + parseFloat(style.paddingBottom)) / 2;
            const currentPaddingX =
                (parseFloat(style.paddingLeft) + parseFloat(style.paddingRight)) / 2;
            const minimumVerticalPadding = (targetSize) =>
                roundUp(currentPaddingY + Math.max(0, targetSize - height) / 2);
            const minimumHorizontalPadding = (targetSize) =>
                roundUp(currentPaddingX + Math.max(0, targetSize - width) / 2);
            issues.push({
                criterion: "2.5.8",
                diagnosis: _t("AA needs 24 × 24 px. Font: %(fontSize)s px.", {
                    fontSize: fontSize.toFixed(1),
                }),
                solution: _t(
                    "Padding (vertical / horizontal) — AA: %(aaPaddingY)s / %(aaPaddingX)s px. AAA: %(aaaPaddingY)s / %(aaaPaddingX)s px.",
                    {
                        aaPaddingX: minimumHorizontalPadding(24),
                        aaPaddingY: minimumVerticalPadding(24),
                        aaaPaddingX: minimumHorizontalPadding(44),
                        aaaPaddingY: minimumVerticalPadding(44),
                    }
                ),
                title: _t("%(label)s: %(width)s × %(height)s px", {
                    height: height.toFixed(1),
                    label,
                    width: width.toFixed(1),
                }),
                url: `${WCAG_URL}target-size-minimum`,
            });
        }
    }
    probe.remove();
    return issues;
};

export class ThemeAccessibilityDialog extends Component {
    static template = "website.ThemeAccessibilityDialog";
    static components = { Dialog };
    props = useProps({
        close: t.function(),
        containerId: t.string(),
        document: t.any(),
        title: t.string(),
    });

    setup() {
        this.state = proxy({ isChecking: true, issues: [], showLoading: false });
        this.check = CHECKS[this.props.containerId];
        onMounted(() => {
            this.loadingTimer = setTimeout(() => (this.state.showLoading = true), 2000);
            this.analysisTimer = setTimeout(() => this.analyze());
        });
        onWillUnmount(() => {
            clearTimeout(this.analysisTimer);
            clearTimeout(this.loadingTimer);
        });
    }

    analyze() {
        if (this.props.containerId === "theme-button") {
            this.state.issues = analyzeTargets(this.props.document, "button");
        } else if (this.props.containerId === "theme-input") {
            this.state.issues = analyzeTargets(this.props.document, "input");
        }
        clearTimeout(this.loadingTimer);
        this.state.isChecking = false;
        this.state.showLoading = false;
    }
}
