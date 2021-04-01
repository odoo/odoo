/** @odoo-module **/
import { useService } from "../core/hooks";
import { debounce } from "../utils/timing";
import { serviceRegistry } from "../webclient/service_registry";

const { Component, core, hooks } = owl;
const { EventBus } = core;
const { onMounted, onWillUnmount, useRef } = hooks;

export const SIZES = { XS: 0, VSM: 1, SM: 2, MD: 3, LG: 4, XL: 5, XXL: 6 };

/**
 * This hook will set the UI active element
 * when the caller component will mount/unmount.
 *
 * The caller component could pass a `t-ref` value of its template
 * to delegate the UI active element to another element than itself.
 * In that case, it is mandatory that the referenced element is fixed and
 * not dynamically attached in/detached from the DOM (e.g. with t-if directive).
 *
 * @param {string} refName
 */
export function useActiveElement(refName = null) {
  const uiService = useService("ui");
  const owner = refName ? useRef(refName) : Component.current;
  onMounted(() => {
    uiService.activateElement(owner.el);
  });
  onWillUnmount(() => {
    uiService.deactivateElement(owner.el);
  });
}

export const uiService = {
  deploy(env) {
    let ui = {};

    // block/unblock code
    const bus = new EventBus();

    let blockCount = 0;
    function block() {
      blockCount++;
      if (blockCount === 1) {
        bus.trigger("BLOCK");
      }
    }
    function unblock() {
      blockCount = Math.max(0, blockCount - 1);
      if (blockCount === 0) {
        bus.trigger("UNBLOCK");
      }
    }

    Object.assign(ui, {
      bus,
      block,
      unblock,
    });

    Object.defineProperty(ui, "isBlocked", {
      get() {
        return blockCount > 0;
      },
    });

    // UI active element code
    let activeElems = [document];

    function activateElement(el) {
      activeElems.push(el);
      bus.trigger("active-element-changed", el);
    }
    function deactivateElement(el) {
      activeElems = activeElems.filter((x) => x !== el);
      bus.trigger("active-element-changed", ui.activeElement);
    }
    function getVisibleElements(selector) {
      const visibleElements = [];
      for (const el of ui.activeElement.querySelectorAll(selector)) {
        const isVisible = el.offsetWidth > 0 && el.offsetHeight > 0;
        if (isVisible) {
          visibleElements.push(el);
        }
      }
      return visibleElements;
    }

    Object.assign(ui, {
      activateElement,
      deactivateElement,
      getVisibleElements,
    });
    Object.defineProperty(ui, "activeElement", {
      get() {
        return activeElems[activeElems.length - 1];
      },
    });

    // window size handling
    const MEDIAS = [
      window.matchMedia("(max-width: 474px)"),
      window.matchMedia("(min-width: 475px) and (max-width: 575px)"),
      window.matchMedia("(min-width: 576px) and (max-width: 767px)"),
      window.matchMedia("(min-width: 768px) and (max-width: 991px)"),
      window.matchMedia("(min-width: 992px) and (max-width: 1199px)"),
      window.matchMedia("(min-width: 1200px) and (max-width: 1533px)"),
      window.matchMedia("(min-width: 1534px)"),
    ];
    function getSize() {
      return MEDIAS.findIndex((media) => media.matches);
    }

    // listen to media query status changes
    function updateSize() {
      ui.size = getSize();
    }
    MEDIAS.forEach((media) => media.addEventListener("change", debounce(updateSize, 100)));

    Object.assign(ui, {
      size: getSize(),
    });
    Object.defineProperty(ui, "isSmall", {
      get() {
        return ui.size <= SIZES.SM;
      },
    });
    Object.defineProperty(env, "isSmall", {
      get() {
        return ui.size <= SIZES.SM;
      },
    });

    return ui;
  },
};

serviceRegistry.add("ui", uiService);
