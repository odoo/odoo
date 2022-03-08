/** @odoo-module **/

import { useDebugCategory } from "@web/core/debug/debug_context";
import { useSetupAction } from "@web/webclient/actions/action_hook";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { evaluateExpr } from "@web/core/py_js/py";

const { useComponent, useEffect, xml } = owl;

export function useSetupView(params) {
    const component = useComponent();
    useDebugCategory("view", { component });
    useSetupAction(params);
}

export function useViewArch(arch, params = {}) {
    const CATEGORY = "__processed_archs__";

    arch = arch.trim();
    const processedRegistry = registry.category(CATEGORY);

    let processedArch;
    if (!processedRegistry.contains(arch)) {
        processedArch = {};
        processedRegistry.add(arch, processedArch);
    } else {
        processedArch = processedRegistry.get(arch);
    }

    const { compile, extract } = params;
    if (!("template" in processedArch) && compile) {
        processedArch.template = xml`${compile(arch)}`;
    }
    if (!("extracted" in processedArch) && extract) {
        processedArch.extracted = extract(arch);
    }

    return processedArch;
}

/**
 * Allows for a component (usually a View component) to handle links with
 * attribute type="action". This is used to support onboarding banners and content helpers.
 *
 * A @web/core/concurrency:KeepLast must be present in the owl environment to allow coordinating
 * between clicks. (env.keepLast)
 *
 * Note that this is similar but quite different from action buttons, since action links
 * are not dynamic according to the record.
 * @param {Object} params
 * @param  {String} params.resModel The default resModel to which actions will apply
 * @param  {Function} [params.reload] The function to execute to reload, if a button has data-reload-on-close
 */
export function useActionLinks({ resModel, reload }) {
    const component = useComponent();
    const keepLast = component.env.keepLast;

    const orm = useService("orm");
    const { doAction } = useService("action");

    function checkAndCollapseBootstrap(target) {
        // the handler should have stopped the Event
        // But we still need to alert bootstrap if we need to
        // This function should be removed when we get rid of bootstrap as a JS framework
        if (target.dataset.toggle === "collapse") {
            $(target).trigger("click.bs.collapse.data-api");
        }
    }

    async function handler(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        let target = ev.target;
        if (target.tagName !== "A") {
            target = target.closest("a");
        }
        const data = target.dataset;

        if (data.method !== undefined && data.model !== undefined) {
            const options = {};
            if (data.reloadOnClose) {
                options.onClose = reload || (() => component.render());
            }
            const action = await keepLast.add(orm.call(data.model, data.method));
            if (action !== undefined) {
                keepLast.add(Promise.resolve(doAction(action, options)));
            }
        } else if (target.getAttribute("name")) {
            const options = {};
            if (data.context) {
                options.additionalContext = evaluateExpr(data.context);
            }
            keepLast.add(doAction(target.getAttribute("name"), options));
        } else {
            let views;
            const resId = data.resid ? parseInt(data.resid, 10) : null;
            if (data.views) {
                views = evaluateExpr(data.views);
            } else {
                views = resId
                    ? [[false, "form"]]
                    : [
                          [false, "list"],
                          [false, "form"],
                      ];
            }
            const action = {
                name: target.getAttribute("title") || target.textContent.trim(),
                type: "ir.actions.act_window",
                res_model: data.model || resModel,
                target: "current",
                views,
                domain: data.domain ? evaluateExpr(data.domain) : [],
            };
            if (resId) {
                action.res_id = resId;
            }

            const options = {};
            if (data.context) {
                options.additionalContext = evaluateExpr(data.context);
            }
            keepLast.add(doAction(action, options));
        }
        checkAndCollapseBootstrap(target);
    }

    return (ev) => {
        const a = ev.target.closest(`a[type="action"]`);
        if (a && ev.currentTarget.contains(a)) {
            handler(ev);
        }
    };
}

export function useBounceButton(containerRef, shouldBounce) {
    let timeout;
    const ui = useService("ui");
    useEffect(
        (containerEl) => {
            if (!containerEl) {
                return;
            }
            const handler = (ev) => {
                const button = ui.activeElement.querySelector("[data-bounce-button]");
                if (button && shouldBounce(ev.target)) {
                    button.classList.add("o_catch_attention");
                    browser.clearTimeout(timeout);
                    timeout = browser.setTimeout(() => {
                        button.classList.remove("o_catch_attention");
                    }, 400);
                }
            };
            containerEl.addEventListener("click", handler);
            return () => containerEl.removeEventListener("click", handler);
        },
        () => [containerRef.el]
    );
}
